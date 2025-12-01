from django.db import models

class Author(models.Model):
    name = models.CharField(max_length=100)
    height = models.IntegerField()
    mass = models.IntegerField()
    hair_color = models.CharField(max_length=100)
    skin_color = models.CharField(max_length=100)
    eye_color = models.CharField(max_length=100)
    birth_year = models.CharField(max_length=100)
    gender = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Starships(models.Model):
    name = models.CharField(max_length=100)
    model = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100)
    cost_in_credits = models.IntegerField()
    length = models.FloatField()
    max_atmosphering_speed = models.IntegerField()
    crew = models.IntegerField()
    passengers = models.IntegerField()
    cargo_capacity = models.IntegerField()
    consumables = models.CharField(max_length=100)
    hyperdrive_rating = models.FloatField()
    MGLT = models.IntegerField()
    starship_class = models.CharField(max_length=100)

    pilots = models.ManyToManyField(
        Author,
        related_name='starships',
    )

    def __str__(self):
        return self.name
