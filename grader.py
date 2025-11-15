"""
This is used to automatically grade all the students projects in a folder.
It will run each project and will use AI to compare it to the expectedOutput
Then Ai will give feedback on the code quality based on the projDescription
Everything will be stored in a json file

structure:
python3 grader.py --folderPath --expectedOutput.txt --projDescription.txt (optional)

It will go through each project in folderPath, unzip the project, compile all the java class
and then execute the file containing main and compare the result to the expected output.

DEMO:
python grader.py --folderPath /home/him/Code/PyCharm/JavaGrader/Test1/testFiles --projDescription /home/him/Code/PyCharm/JavaGrader/Test1/test1ProjDesc.txt --expectedOutput /home/him/Code/PyCharm/JavaGrader/Test1/test1Output.txt

python grader.py --folderPath /home/him/Code/PyCharm/JavaGrader/Test2/projects --projDescription /home/him/Code/PyCharm/JavaGrader/Test2/desc.txt --expectedOutput /home/him/Code/PyCharm/JavaGrader/Test2/exp.txt
"""

import argparse, os, json, sys, pprint
import subprocess, shutil, re, time
from pathlib import Path
from google import genai

# Create key
with open("keys.json", "r") as f:
    key = json.load(f)["key1"]
client = genai.Client(api_key=key)

# Read prompt instructions from file
with open("prompt_instructions.txt", "r") as f:
    prompt_instructions = f.read()

"""
ARUGMENTS
"""

# Argument parser
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folderPath", required=True, type=str, help="Path to the folder containing the projects")
    parser.add_argument("--projDescription", type=str, help="Path to the project description file")
    parser.add_argument("--expectedOutput", type=str, help="Path to the expected output file")
    parser.add_argument("--fileExtensions", type=str, default=[".java"], nargs="*", help="language to check for: java, python, c++")
    parser.add_argument("--no-ai", dest="ai", action="store_false", help="Disable AI feedback")
    parser.set_defaults(ai=True)
    return parser.parse_args()

# Reads and verifies arguments
def clean_args(args) -> tuple[str, str, set[str]]:
    try:
        projDescription = Path(args.projDescription).read_text()
    except TypeError:
        projDescription = "No Project Description Given"
    except FileNotFoundError as e:
        print(f"Error: {e}. Defaulting projDescription")
        projDescription = "No Project Description Given"

    try:
        expectedOutput = Path(args.expectedOutput).read_text()
    except TypeError:
        expectedOutput = "No Expected Output Given"
    except FileNotFoundError as e:
        print(f"Error: {e}. Defaulting expectedOutput")
        expectedOutput = "No Expected Output Given"

    # normalize extensions: allow "java" or ".java" and make lowercase
    ext_list = set((e if e.startswith('.') else f'.{e}').lower() for e in args.fileExtensions)

    return expectedOutput, projDescription, ext_list

"""
READ / COMPILE / RUN (Java)
"""

def compile_java(target: Path, build_path: Path):
    """
    Compile all .java sources under `target` (dir) or under `target.parent` (file)
    into `build_path`. Returns (ok: bool, log: str, out_dir: Path).

    - Uses a memo to avoid recompiling the same tree multiple times in one process.
    - Writes classes into a dedicated .build folder to keep submissions clean.
    - Uses an @sources.txt argfile to dodge command-line length limits with many files.
    """
    # determine src root
    src_root = target if target.is_dir() else target.parent
    src_root = src_root.resolve()
    build_path = build_path.resolve()

    # memoize to avoid recompiling same project
    if not hasattr(compile_java, "_compiled_roots"):
        compile_java._compiled_roots = set()
    if src_root in compile_java._compiled_roots:
        return True, f"Already compiled: {src_root}", build_path

    if shutil.which("javac") is None:
        return False, "javac not found on PATH", build_path

    sources = [str(p) for p in src_root.rglob("*.java")]
    if not sources:
        return False, f"No .java sources under {src_root}", build_path

    try:
        build_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"Failed to create build dir {build_path}: {e}", build_path

    argfile = build_path / "sources.txt"
    try:
        argfile.write_text("\n".join(sources), encoding="utf-8")
    except Exception as e:
        return False, f"Failed to write argfile: {e}", build_path

    cmd = [
        "javac",
        "-encoding", "UTF-8",
        "-d", str(build_path),
        "@" + str(argfile),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return False, f"Failed to invoke javac: {e}", build_path

    out = (proc.stdout or "") + (proc.stderr or "")
    ok = proc.returncode == 0
    if ok:
        compile_java._compiled_roots.add(src_root)
    try:
        (build_path / "compile.log").write_text(out, encoding="utf-8", errors="ignore")
    except Exception:
        pass
    return ok, out, build_path

# Regexes (thanks chatgpt):
# - MAIN_RE: supports String[] args or String... args, any var name, and flexible whitespace.
MAIN_RE = re.compile(
    r'public\s+static\s+void\s+main\s*\(\s*String(?:\[\]|\.\.\.)\s+\w+\s*\)',
    re.I
)
# - PKG_RE: capture optional package declaration.
PKG_RE  = re.compile(r'^\s*package\s+([\w\.]+)\s*;\s*$', re.M)
# - CLASS_RE: capture class declarations; we later map which class encloses the main() hit.
CLASS_RE = re.compile(r'\b(public\s+)?class\s+([A-Za-z_]\w*)\b', re.M)

def find_java_main_classes(root: Path) -> list[str]:
    """
    Return FQCNs by finding the class that **encloses** a main(...) in each file.
    If we can't locate the enclosing class, we fall back to the file stem (or first public class).
    """
    mains: list[str] = []
    for f in root.rglob('*.java'):
        try:
            s = f.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        m_main = MAIN_RE.search(s)
        if not m_main:
            continue

        # package (optional)
        pkg = None
        m_pkg = PKG_RE.search(s)
        if m_pkg:
            pkg = m_pkg.group(1)

        # find the class that contains the main() occurrence
        main_pos = m_main.start()
        class_name = None

        # build a list of class spans (start idx, name); next class start is end of span
        class_hits = list(CLASS_RE.finditer(s))
        for i, m in enumerate(class_hits):
            cls_start = m.start()
            cls_name = m.group(2)
            cls_end = class_hits[i+1].start() if i+1 < len(class_hits) else len(s)
            if cls_start <= main_pos < cls_end:
                class_name = cls_name
                break

        # fallback: first public class, else file stem
        if class_name is None:
            pub = next((m for m in class_hits if m.group(1)), None)
            class_name = pub.group(2) if pub else f.stem

        fqcn = f"{pkg}.{class_name}" if pkg else class_name
        mains.append(fqcn)

    return mains

def run_java_main(project_path: Path, timeout_s: int = 12) -> dict:
    build_dir = (project_path / '.build').resolve()
    if not build_dir.exists():
        return dict(ok=False, rc=1, stdout='', stderr='Build dir not found', elapsed=0.0, fqcn=None)

    mains = find_java_main_classes(project_path)
    if not mains:
        return dict(ok=False, rc=1, stdout='', stderr='No main() class found', elapsed=0.0, fqcn=None)

    fqcn = mains[0]
    t0 = time.time()
    try:
        proc = subprocess.run(
            ['java', '-cp', str(build_dir), fqcn],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(project_path)  # <-- run from project root so relative file paths work
        )
        dt = time.time() - t0
        print(f"\tOutput:\n{proc.stdout}")
        return dict(ok=(proc.returncode == 0), rc=proc.returncode,
                    stdout=proc.stdout or '', stderr=proc.stderr or '',
                    elapsed=round(dt, 3), fqcn=fqcn)
    except subprocess.TimeoutExpired:
        print("\tTimed Out")
        return dict(ok=False, rc=124, stdout='', stderr='Timeout', elapsed=float(timeout_s), fqcn=fqcn)
    except Exception as e:
        print(f"\tException: {e}")
        return dict(ok=False, rc=1, stdout='', stderr=f'Run failed: {e}', elapsed=0.0, fqcn=fqcn)

# Reads all code from the project path (including sub directories) and pastes together as a string
def read_code_from_proj(projectPath: Path, ext_set: set[str]) -> str:
    print(f"\nReading code from {projectPath}")

    code = ""
    java_found = False
    for file in projectPath.rglob("*"):
        if file.is_file() and file.suffix.lower() in ext_set:
            try:
                code += f"\nFile: {file.relative_to(projectPath)}\n"
                code += file.read_text(encoding="utf-8", errors="ignore")
                print(f"\t Read: {file.relative_to(projectPath)}")
            except Exception as e:
                print(f"\t Skip (read error): {file} ({e})")

            if file.suffix.lower() == ".java":
                java_found = True

    # compile Java once per project (if any .java present)
    if java_found:
        ok, log, out_dir = compile_java(projectPath, projectPath / ".build")
        status = "OK" if ok else "FAIL"
        print(f"\t Java compile: {status} -> {out_dir}")
        if not ok:
            print(log)

    return code

"""
AI PROMPTING
"""

# trims the length of the output so that the text is not too long
def trim_length(s: str, limit: int = 4900) -> str:
    if s is None:
        return ""
    s = s.strip()

    if len(s) > limit:
        print(f"Length {len(s)} too long for {limit}, trimming")
        return s[:limit] + f"\n…[truncated {len(s) - limit} chars]"

    return s

# Prompt AI and get the formatted json
def prompt_ai(code: str, expectedOutput: str, projDescription: str, actualOutput: str) -> str:
    # NOTE: We include Actual Program Output so the reviewer can judge logic vs formatting.
    code = trim_length(code, 19900)
    actualOutput = trim_length(actualOutput, 19900)
    prompt = f"""
    INSTRUCTIONS:
    <START>
    {prompt_instructions}
    <END>
    
    Project Description:
    <START>
    {projDescription}
    <END>
    
    Expected Output:
    <START>
    {expectedOutput}
    <END>

    Actual Program Output:
    <START>
    {actualOutput}
    <END>
    
    Student Files: (these are all truncated together with the filename at top)
    <START>
    {code}
    <END>
    """
    print("Getting AI feedback...")
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            # JSON mode makes Gemini emit proper JSON
            config={
                "response_mime_type": "application/json",
                "temperature": 0
            }
        )

        text = (resp.text or "").strip()
        data = json.loads(text)
        pprint.pprint(text)
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        # Catch any expections from api or other
        fallback = {
            "score": 0.0,
            "comments": [f"AI call failed: {type(e).__name__}"],
            "ai": ["NAN"]
        }

        print(f"Error: {type(e).__name__}: {e}")
        return json.dumps(fallback, ensure_ascii=False)

"""
MAIN
"""

# Entry
if __name__ == "__main__":
    args = parse_args()
    proj_folder = Path(args.folderPath)
    use_ai = args.ai
    # Get cleaned arguments
    expectedOutput, projDescription, extension_list = clean_args(args)

    # start a results container
    results = {
        "folderPath": str(proj_folder),
        "results": []
    }

    # Look through each sub_project in the project folder
    for sub_project in os.listdir(proj_folder):
        current_directory = Path(proj_folder).joinpath(sub_project)
        if not current_directory.is_dir():
            print(f"Skipping non-folder entry: {current_directory.name}")
            continue

        # Read files + compile Java
        code = read_code_from_proj(current_directory, extension_list)

        # Print run info; we prepare data for AI and results.json
        actual_out = ""
        java_present = any(p.is_file() and p.suffix.lower() == ".java" for p in current_directory.rglob("*"))
        run_info = None
        if java_present:
            run_info = run_java_main(current_directory)
            if run_info.get('fqcn'):
                print(f"\t Java run: fqcn={run_info['fqcn']}, rc={run_info['rc']}, elapsed={run_info['elapsed']}s")
            else:
                print(f"\t Java run: {run_info['stderr']}")
            actual_out = run_info.get('stdout', '')

        # If using ai, prompt with actual output included
        if use_ai:
            ai_json = prompt_ai(
                code=code,
                expectedOutput=expectedOutput,
                projDescription=projDescription,
                actualOutput=actual_out
            )
        else:
            # SAFETY: define ai_json even when AI is disabled to avoid NameError below.
            ai_json = json.dumps({
                "Overall score": "N/A",
                "Comments": "AI disabled",
                "AI": "None"
            }, ensure_ascii=False)

        # Assemble entry, including run details (stdout/stderr/rc/time/fqcn)
        result_entry = {
            "submission": sub_project,
            "review": json.loads(ai_json),
            "run": None
        }
        if run_info is not None:
            result_entry["run"] = {
                "ok": run_info["ok"],
                "rc": run_info["rc"],
                "elapsed_sec": run_info["elapsed"],
                "fqcn": run_info["fqcn"],
                "stdout": trim_length(run_info.get("stdout",""), 19900),
                "stderr": trim_length(run_info.get("stderr",""), 5000)
            }
        results["results"].append(result_entry)

    print("Data has been written to results.json")
    out_path = Path("results.json")
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
