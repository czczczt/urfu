from django.urls import path
from . import views

urlpatterns = [
    path("admin-panel/", views.admin_panel, name="admin_panel"),
    path("admin-panel/user/<int:user_id>/", views.admin_user_edit, name="admin_user_edit"),
    path("admin-panel/user/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
    path("", views.main_page, name="main"),
    path("history/", views.history_page, name="history"),
    path("transcription/<int:transcription_id>/", views.transcription_page, name="transcription"),
    path("transcription/<int:transcription_id>/delete/", views.delete_transcription, name="delete_transcription"),
    # Алиас на тот же обработчик: старые ссылки и {% url 'cancel_transcription' %} продолжают работать.
    path("transcription/<int:transcription_id>/cancel/", views.delete_transcription, name="cancel_transcription"),
    path("transcription/<int:transcription_id>/rename_speaker/", views.rename_speaker, name="rename_speaker"),
    path("transcription/<int:transcription_id>/export/", views.export_transcription, name="export_transcription"),
    path("transcription/<int:transcription_id>/share/", views.share_transcription, name="share_transcription"),
    path("transcription/<int:transcription_id>/edit_name/", views.edit_transcription_name, name="edit_transcription_name"),
    path(
        "transcription/<int:transcription_id>/start_transcription/",
        views.start_transcription,
        name="start_transcription",
    ),
    path("transcription/<int:transcription_id>/start_protocol/", views.start_protocol, name="start_protocol"),
    path("load/", views.load_page, name="load"),
    path("video/<int:id_video>/", views.video_page, name="video"),
    path("phrase/", views.phrase_page, name="phrase"),
]
