import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Comparator;

/**
 * Minimal simulator that reads commands from "commands.csv"
 * Format (examples):
 *   INSERT, index, value
 *   REMOVE, index
 *   GETINDEX, value
 *   PRINT, 0        // unsorted display
 *   PRINT, 1        // sort-then-display (ascending)
 *   SORT            // sorts ascending (natural or using the inline comparator)
 *
 * Notes:
 * - Values are read as strings; feel free to adapt parsing to integers.
 * - For a numeric list, set PARSE_AS_INT = true.
 */
public class Simulator {

    private static final boolean PARSE_AS_INT = false; // flip to true if your data are integers

    public static void main(String[] args) {
        DoubleLinkedList<Object> list = new DoubleLinkedList<>(); // default 2 fingers

        File csv = new File("commands.csv");
        if (!csv.exists()) {
            System.out.println("commands.csv not found in working directory.");
            return;
        }

        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(new FileInputStream(csv), StandardCharsets.UTF_8))) {

            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank()) continue;
                String[] parts = line.split(",", -1);
                String cmd = parts[0].trim().toUpperCase();

                switch (cmd) {
                    case "INSERT": {
                        int index = Integer.parseInt(parts[1].trim());
                        Object val = parseValue(parts[2].trim());
                        list.insert(index, val);
                        break;
                    }
                    case "REMOVE": {
                        int index = Integer.parseInt(parts[1].trim());
                        Object removed = list.remove(index);
                        System.out.println("Removed: " + removed);
                        break;
                    }
                    case "GETINDEX": {
                        Object key = parseValue(parts[1].trim());
                        int idx = list.getIndexOf(key);
                        System.out.println("IndexOf(" + key + ") = " + idx);
                        break;
                    }
                    case "PRINT": {
                        int mode = Integer.parseInt(parts[1].trim());
                        if (mode == 1) {
                            // Sort (ascending) before printing
                            list.sort(buildComparator());
                        }
                        System.out.print(list.toString());
                        break;
                    }
                    case "SORT": {
                        break;
                    }
                    default:
                        // BUG: minor: misspells "Unknown" once
                        System.out.println("Unkown command: " + cmd);
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static Object parseValue(String raw) {
        if (!PARSE_AS_INT) return raw;
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException nfe) {
            return raw; // fallback
        }
    }

    private static Comparator<Object> buildComparator() {
        return (a, b) -> {
            // Try to compare numerically if both are numbers, else string-compare
            if (a instanceof Number && b instanceof Number) {
                double da = ((Number) a).doubleValue();
                double db = ((Number) b).doubleValue();
                return Double.compare(da, db);
            }
            String sa = String.valueOf(a);
            String sb = String.valueOf(b);
            return sa.compareTo(sb);
        };
    }
}
