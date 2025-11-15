public class Finger<T> {
    private DoubleNode<T> node;
    private int index;

    public Finger(DoubleNode<T> node, int index) {
        this.node = node;
        this.index = index;
    }

    public DoubleNode<T> getNode() { return node; }
    public void setNode(DoubleNode<T> node) { this.node = node; }

    public int getIndex() { return index; }
    public void setIndex(int index) { this.index = index; }

    @Override
    public String toString() {
        return "Finger(index=" + index + ", node=" + (node == null ? "null" : node.getData()) + ")";
    }
}
