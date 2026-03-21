from django.shortcuts import render
from .models import Author, Starships


def all_characters(request):
    characters = Author.objects.all()
    context = {
        'characters': characters,
    }
    return render(request, 'all/characters_list.html', context)


def character_detail(request, pk):
    character = Author.objects.get(pk=pk)
    starships = character.starships.all()
    context = {
        'character': character,
        'starships': starships,
    }
    return render(request, 'all/character_detail.html', context)


def starship_detail(request, pk):
    starship = Starships.objects.get(pk=pk)
    pilots = starship.pilots.all()
    context = {
        'starship': starship,
        'pilots': pilots,
    }
    return render(request, 'all/starship_detail.html', context)