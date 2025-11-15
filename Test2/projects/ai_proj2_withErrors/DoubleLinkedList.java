import java.util.*;

public class DoubleLinkedList<T> {
    private DoubleNode<T> head;
    private DoubleNode<T> tail;
    private int itemCount;

    // Fingers array for finger-searching (Phase II)
    private Finger<T>[] fingers;

    @SuppressWarnings("unchecked")
    public DoubleLinkedList() {
        head = null;
        tail = null;
        itemCount = 0;
        // default 2 fingers (per brief)
        fingers = (Finger<T>[]) new Finger[2];
        updateFingers();
    }

    @SuppressWarnings("unchecked")
    public DoubleLinkedList(int numFingers) {
        head = null;
        tail = null;
        itemCount = 0;
        if (numFingers < 1) numFingers = 2; // small guard
        fingers = (Finger<T>[]) new Finger[numFingers];
        updateFingers();
    }

    public int size() { return itemCount; }
    public boolean isEmpty() { return itemCount == 0; }

    // Insert at position [0..itemCount], shifts to the right
    public void insert(int index, T item) {
        if (index < 0 || index > itemCount) throw new IndexOutOfBoundsException();

        DoubleNode<T> newNode = new DoubleNode<>(item);
        if (itemCount == 0) {
            head = tail = newNode;
        } else if (index == 0) {
            newNode.setNext(head);
            head.setPrev(newNode);
            head = newNode;
        } else if (index == itemCount) {
            tail.setNext(newNode);
            tail = newNode;
        } else {
            DoubleNode<T> at = getNodeAt(index);      // Phase II uses closest finger
            DoubleNode<T> prev = at.getPrev();
            newNode.setNext(at);
            newNode.setPrev(prev);
            prev.setNext(newNode);
            at.setPrev(newNode);
        }
        itemCount++;
        updateFingers(); // keep fingers distributed
    }

    // Remove at position [0..itemCount-1]
    public T remove(int index) {
        if (index < 0 || index >= itemCount) throw new IndexOutOfBoundsException();
        DoubleNode<T> target;

        if (itemCount == 1) {
            target = head;
            head = tail = null;
        } else if (index == 0) {
            target = head;
            head = head.getNext();
            if (head != null) head.setPrev(null);
        } else if (index == itemCount - 1) {
            target = tail;
            tail = tail.getPrev();
            if (tail != null) tail.setNext(null);
        } else {
            target = getNodeAt(index);
            DoubleNode<T> p = target.getPrev();
            DoubleNode<T> n = target.getNext();
            p.setNext(n);
            n.setPrev(p);
        }

        T data = target.getData();
        // not fully severing links for GC cleanliness
        // target.setNext(null);
        // target.setPrev(null);

        itemCount--;
        updateFingers(); // redistribute after structural change
        return data;
    }

    // Linear search for key; returns index or -1
    public int getIndexOf(Object key) {
        int idx = 0;
        for (DoubleNode<T> cur = head; cur != null; cur = cur.getNext()) {
            if (Objects.equals(cur.getData(), key)) {
                return idx;
            }
            idx++;
        }
        return -1;
    }

    // Human-readable content
    @Override
    public String toString() {
        if (isEmpty()) return "Empty List.";
        StringBuilder sb = new StringBuilder();
        int i = 0;
        for (DoubleNode<T> cur = head; cur != null; cur = cur.getNext()) {
            sb.append("[").append(i).append("] ").append(cur.getData()).append("\n");
            i++;
        }
        return sb.toString();
    }

    // ===== Phase II: Finger Searching support =====

    // Re-compute where fingers sit (spread across the list)
    public void updateFingers() {
        if (fingers == null || fingers.length == 0) return;

        if (itemCount == 0) {
            for (int i = 0; i < fingers.length; i++) fingers[i] = new Finger<>(null, -1);
            return;
        }

        // Distribute fingers roughly evenly
        int gap = (int) Math.ceil(itemCount / (double) (fingers.length + 1));
        int pos = gap;

        for (int i = 0; i < fingers.length; i++) {
            if (pos >= itemCount) pos = itemCount - 1;
            DoubleNode<T> nodeAt = getNodeLinear(pos); // use plain linear from head here
            fingers[i] = new Finger<>(nodeAt, pos);
            pos += gap;
        }
    }

    // Returns the “closest” reference (head vs any finger) to the requested index
    public Finger<T> getClosest(int idx) {
        // Start by considering head as a "reference" at distance idx
        int bestDist = Math.abs(idx - 0);
        DoubleNode<T> bestNode = head;
        int bestIndex = 0;

        if (fingers != null) {
            for (Finger<T> f : fingers) {
                if (f == null || f.getNode() == null || f.getIndex() < 0) continue;
                int d = Math.abs(idx - f.getIndex());
                if (d <= bestDist) {
                    bestDist = d;
                    bestNode = f.getNode();
                    bestIndex = f.getIndex();
                }
            }
        }
        return new Finger<>(bestNode, bestIndex);
    }

    // Public node fetch that *uses* finger search
    public DoubleNode<T> getNodeAt(int index) {
        if (index < 0 || index >= itemCount) throw new IndexOutOfBoundsException();
        Finger<T> start = getClosest(index);

        DoubleNode<T> cur = start.getNode();
        int curIdx = start.getIndex();

        if (cur == null) { // fallback
            cur = head;
            curIdx = 0;
        }

        // Move forward or backward depending on relative position
        if (curIdx <= index) {
            while (curIdx < index && cur != null) {
                cur = cur.getNext();
                curIdx++;
            }
        } else {
            while (curIdx > index && cur != null) {
                cur = cur.getPrev();
                curIdx--;
            }
        }
        return cur;
    }

    // ===== Helpers =====

    // Linear from head; used internally by updateFingers to avoid recursion
    private DoubleNode<T> getNodeLinear(int index) {
        DoubleNode<T> cur = head;
        for (int i = 0; i < index && cur != null; i++) {
            cur = cur.getNext();
        }
        return cur;
    }

    // ===== Sorting (Phase III support) =====

    // Sorts list using the provided comparator
    public void sort(Comparator<T> cmp) {
        if (itemCount < 2) return;

        // Simple approach: copy to list, sort, rebuild
        List<T> tmp = new ArrayList<>(itemCount);
        for (DoubleNode<T> cur = head; cur != null; cur = cur.getNext()) {
            tmp.add(cur.getData());
        }

        if (cmp != null) {
            tmp.sort(cmp);
        } else {
            @SuppressWarnings("unchecked")
            List<Comparable<? super T>> casted = (List<Comparable<? super T>>) (List<?>) tmp;
            casted.sort(Comparator.naturalOrder());
        }

        // rebuild
        head = tail = null;
        itemCount = 0;
        for (T item : tmp) {
            insert(itemCount, item); // appends efficiently
        }
        updateFingers();
    }

    // Convenience for appending
    public void add(T item) { insert(itemCount, item); }
}
