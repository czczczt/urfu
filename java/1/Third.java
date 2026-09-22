import java.util.Scanner;

public class Third {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        int x = scanner.nextInt();
        int y = scanner.nextInt();

        if (x != y){
            int xx = x + y;
            int yy = x + y;
            System.out.println(xx);
            System.out.println(yy);
        } else {
            int xx = 0;
            int yy = 0;
            System.out.println(xx);
            System.out.println(yy);
        }
    }
}


