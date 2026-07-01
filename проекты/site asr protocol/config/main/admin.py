from django.contrib import admin
from .models import File, Transcription, Result, RouteAccess


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "extension", "owner", "load_datetime")
    list_filter = ("extension", "load_datetime")
    search_fields = ("name", "path_to_file", "owner__login")


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "file", "initializer", "status", "execution_datetime", "edit_datetime")
    list_filter = ("status",)
    search_fields = ("file__name", "initializer__login")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("id", "transcription", "speaker", "text_preview", "phrase_start_time", "phrase_end_time")
    list_filter = ("speaker",)
    search_fields = ("speaker", "text")
    ordering = ("phrase_start_time",)

    def text_preview(self, obj):
        return obj.text[:50] + "..." if len(obj.text) > 50 else obj.text

    text_preview.short_description = "Текст"


@admin.register(RouteAccess)
class RouteAccessAdmin(admin.ModelAdmin):
    list_display = ("id", "method", "uri", "access")
    list_filter = ("method", "access")
    search_fields = ("uri",)
