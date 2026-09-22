import java.util.Scanner;

public class Second {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        double x = scanner.nextDouble();
        double y = x * Math.sqrt(x) + Math.pow(x, 5) + Math.exp(x);
        System.out.println(y);
    }
}


