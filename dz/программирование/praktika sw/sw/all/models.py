from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    height = models.IntegerField(null=True, blank=True)
    mass = models.IntegerField(null=True, blank=True)
    hair_color = models.CharField(max_length=100, null=True, blank=True)
    skin_color = models.CharField(max_length=100, null=True, blank=True)
    eye_color = models.CharField(max_length=100, null=True, blank=True)
    birth_year = models.CharField(max_length=100, null=True, blank=True)
    gender = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Starships(models.Model):
    name = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    manufacturer = models.CharField(max_length=100)
    cost_in_credits = models.IntegerField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    max_atmosphering_speed = models.IntegerField(null=True, blank=True)
    crew = models.IntegerField(null=True, blank=True)
    passengers = models.IntegerField(null=True, blank=True)
    cargo_capacity = models.IntegerField(null=True, blank=True)
    consumables = models.CharField(max_length=100, null=True, blank=True)
    hyperdrive_rating = models.FloatField(null=True, blank=True)
    MGLT = models.IntegerField(null=True, blank=True)
    starship_class = models.CharField(max_length=100)

    pilots = models.ManyToManyField(
        Author,
        related_name='starships',
        blank=True
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
