// Comments.java; sample } with fake tokens ;;; }}}
package sample;

/**
 * Block comment ; with braces } and more ;
 * still inside comment;
 */
public class Comments {
    // int should_not_count = 1; { } ;
    public int compute() {
        int a = 1; // trailing comment ; }
        int b = 2; /* inline block ; } */ int c = 3;
        return a + b + c;
    }
}
