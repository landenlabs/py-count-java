package nested;

public class Nested {
    public void loop() {
        for (int i = 0; i < 3; i++) {
            if (i == 1) {
                continue;
            }
            System.out.println(i);
        }
    }
}
