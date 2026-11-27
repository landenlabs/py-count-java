// leading comment; with a fake semicolon and brace }
class ForLoop {
    void run() {
        /* block comment ; } */
        String s = "a;b}c";
        char c = ';';
        for (int i = 0, j = helper(1, 2); i < 10; i++) {
            total += i;
        }
        for (String x : list) {
            System.out.println(x);
        }
    }
}
