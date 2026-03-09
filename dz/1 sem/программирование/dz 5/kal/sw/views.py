from django.shortcuts import render
from django.http import JsonResponse, HttpResponse

import requests
import json

def get_luke_info(request):
    response = requests.get('https://swapi.dev/api/people/1')
    if response.status_code == 200:
        data = response.json()
        return render(request, 'sw/luke_skywalker/personal.html', data)
    return HttpResponse('Не удалось найти инфы')  # обработка исключения

def imperial_shuttle_info(request):
    response = requests.get('https://swapi.dev/api/starships/22/')
    return render(request, 'sw/imperial-shuttle/imperial-shuttle.html', response.json())

def snowspeeder_info(request):
    response = requests.get('https://swapi.dev/api/vehicles/14/')
    return render(request, 'sw/snowspeeder/snowspeeder.html', response.json())

def xwing_info(request):
    response = requests.get('https://swapi.dev/api/starships/12/')
    return render(request, 'sw/xwing/xwing.html', response.json())

