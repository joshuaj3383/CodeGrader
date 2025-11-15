#Java Project Grader

This is used to automatically grade all the students projects in a folder.
It will run each project and will use AI to compare it to the expectedOutput
Then Ai will give feedback on the code quality based on the projDescription
Everything will be stored in a json file

structure:
python3 grader.py --folderPath --expectedOutput.txt --projDescription.txt (optional)

It will go through each project in folderPath, unzip the project, compile all the java class
and then execute the file containing main and compare the result to the expected output.

DEMO (FILL IN APPROPRIATE PATHS):
python grader.py --folderPath /Test1/testFiles --projDescription /Test1/test1ProjDesc.txt --expectedOutput /Test1/test1Output.txt

python grader.py --folderPath /Test2/projects --projDescription /Test2/desc.txt --expectedOutput /Test2/exp.txt
