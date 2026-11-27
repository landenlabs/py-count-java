public class Strings {
    public void run() {
        String a = "value;with;semicolons}and}braces";
        char c = ';';
        char brace = '}';
        String multiline = """
                line one ; }
                line two ; }
                """;
        System.out.println(a + c + brace + multiline);
    }
}
