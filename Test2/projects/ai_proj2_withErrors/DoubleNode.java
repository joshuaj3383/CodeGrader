public class DoubleNode<T> {
    private T data;
    private DoubleNode<T> next;
    private DoubleNode<T> prev;

    public DoubleNode(T data) {
        this(data, null, null);
    }

    public DoubleNode(T data, DoubleNode<T> next, DoubleNode<T> prev) {
        this.data = data;
        this.next = next;
        this.prev = prev; // initializes prev as required
    }

    public T getData() { return data; }
    public void setData(T data) { this.data = data; }

    public DoubleNode<T> getNext() { return next; }
    public void setNext(DoubleNode<T> next) { this.next = next; }

    public DoubleNode<T> getPrev() { return prev; }
    public void setPrev(DoubleNode<T> prev) { this.prev = prev; }
}
