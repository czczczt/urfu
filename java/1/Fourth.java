import java.util.Scanner;

public class Fourth {
    public static void main(String[] args) {
        String text = "Расчёт стоимости товара без НДС";
        System.out.println(text);

        Scanner scanner = new Scanner(System.in);
        System.out.print("Введите цену товара: ");
        double price = scanner.nextDouble();
        if (price <= 0) {
            System.out.print("Цена не может быть отрицательной или равной нулю");
            System.exit(0);
        }
        System.out.print("Введите НДС: ");
        int percent = scanner.nextInt();
        if (0 > percent) {
            System.out.print("НДС не может быть отрицательным");
            System.exit(0);
        }

        double without = (price / (100 + percent)) * 100;
        System.out.printf("Стоимость товара: %.2f%n", without);
    }
}


