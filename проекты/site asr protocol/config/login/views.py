from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render


def auth_page(request):
    if request.user.is_authenticated:
        return redirect("main")

    if request.method == "POST":
        user_login = request.POST.get("login", "").strip()
        password = request.POST.get("password", "")

        if not user_login or not password:
            return render(request, "auth.html", {"error": "Заполните все поля."})

        user = authenticate(request, login=user_login, password=password)
        if user is not None:
            login(request, user)
            return redirect("main")

        return render(request, "auth.html", {"error": "Неверный логин или пароль.", "login_value": user_login})

    return render(request, "auth.html")


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect("auth")