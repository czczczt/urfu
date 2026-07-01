from django.db import models


class File(models.Model):
    name = models.CharField(max_length=255)
    extension = models.CharField(max_length=32)
    owner = models.ForeignKey("login.User", on_delete=models.CASCADE, related_name="files")
    load_datetime = models.DateTimeField()
    path_to_file = models.TextField()

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"
        ordering = ["-load_datetime"]

    def __str__(self) -> str:
        return f"{self.name}.{self.extension}"


class Transcription(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "В ожидании"
        PROCESSING = "processing", "Обрабатывается"
        COMPLETED = "completed", "Завершено"
        FAILED = "failed", "Ошибка"

    class ProtocolStatus(models.TextChoices):
        NOT_STARTED = "not_started", "Не запущено"
        PROCESSING = "processing", "Выполняется"
        COMPLETED = "completed", "Завершено"
        FAILED = "failed", "Ошибка"

    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="transcriptions")
    name = models.CharField(max_length=255, default="Без названия")
    description = models.TextField(blank=True, null=True)
    initializer = models.ForeignKey(
        "login.User", on_delete=models.CASCADE, related_name="initialized_transcriptions"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    protocol_status = models.CharField(
        max_length=20,
        choices=ProtocolStatus.choices,
        default=ProtocolStatus.NOT_STARTED,
    )
    execution_datetime = models.DateTimeField(blank=True, null=True)
    edit_datetime = models.DateTimeField(blank=True, null=True)

    @property
    def effective_status(self) -> str:
        """Статус для UI: failed с уже сохранёнными результатами считаем завершённым."""
        if self.status == self.Status.FAILED:
            prefetched = getattr(self, "_prefetched_objects_cache", None)
            if prefetched is not None and "results" in prefetched:
                if prefetched["results"]:
                    return self.Status.COMPLETED
            elif self.results.exists():
                return self.Status.COMPLETED
        return self.status

    @property
    def needs_poll(self) -> bool:
        if self.effective_status in (self.Status.PENDING, self.Status.PROCESSING):
            return True
        return (
            self.effective_status == self.Status.COMPLETED
            and self.protocol_status == self.ProtocolStatus.PROCESSING
        )

    class Meta:
        verbose_name = "Транскрибация"
        verbose_name_plural = "Транскрибации"
        ordering = ["-execution_datetime", "-id"]

    def __str__(self) -> str:
        meeting_name = self.file.name if getattr(self, "file", None) else self.name
        return f"{meeting_name} - {self.execution_datetime.date() if self.execution_datetime else 'Не выполнена'}\nСтатус: {self.get_status_display()}\nОписание: {self.description or 'Нет описания'}\n"

    def get_formatted_output(self) -> str:
        def _fmt_mmss(seconds: float) -> str:
            try:
                total = max(int(float(seconds)), 0)
            except (TypeError, ValueError):
                total = 0
            minutes = total // 60
            sec = total % 60
            return f"{minutes:02d}:{sec:02d}"

        month_names = {
            1: "января",
            2: "февраля",
            3: "марта",
            4: "апреля",
            5: "мая",
            6: "июня",
            7: "июля",
            8: "августа",
            9: "сентября",
            10: "октября",
            11: "ноября",
            12: "декабря",
        }
        upload_time_str = self.file.load_datetime.strftime("%H:%M") if getattr(self.file, "load_datetime", None) else ""
        meeting_name = (self.file.name or self.name or "Без названия").strip()
        if self.execution_datetime:
            dt = self.execution_datetime
            date_human = f"{dt.day:02d} {month_names.get(dt.month, '')} {dt.year}".strip()
        else:
            date_human = "дата не указана"
        if upload_time_str:
            output = f'Протокол встречи "{meeting_name}" {upload_time_str} {date_human}\n\n'
        else:
            output = f'Протокол встречи "{meeting_name}" {date_human}\n\n'
        protocol = None
        try:
            protocol = self.protocol
        except Exception:
            protocol = None

        brief = str(self.description or "").strip()
        if not brief and protocol:
            brief = str(protocol.brief_text or "").strip()
        if brief:
            output += f"\n## Краткая выжимка\n\n{brief}\n"

        if protocol and str(protocol.protocol_text).strip():
            output += f"\n## Пересказ встречи\n\n{str(protocol.protocol_text).strip()}\n"
        if protocol and str(protocol.compressed_text).strip():
            output += f"\n## Пересказ по блокам\n\n{str(protocol.compressed_text).strip()}\n"

        output += "\n## Транскрибация\n"
        results = self.results.all()
        for res in results:
            output += f"\n### {res.speaker} `{_fmt_mmss(res.phrase_start_time)}`\n\n{res.text}\n"

        return output


class Result(models.Model):
    transcription = models.ForeignKey(
        Transcription, on_delete=models.CASCADE, related_name="results"
    )
    speaker = models.CharField(max_length=100)
    text = models.TextField()
    phrase_start_time = models.FloatField()
    phrase_end_time = models.FloatField()

    class Meta:
        verbose_name = "Результат"
        verbose_name_plural = "Результаты"
        ordering = ["phrase_start_time"]

    def __str__(self) -> str:
        return f"{self.speaker}: {self.text[:50]}..."


class MeetingProtocol(models.Model):
    transcription = models.OneToOneField(
        Transcription,
        on_delete=models.CASCADE,
        related_name="protocol",
    )
    brief_text = models.TextField(blank=True, default="")
    protocol_text = models.TextField()
    compressed_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Протокол встречи"
        verbose_name_plural = "Протоколы встреч"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Protocol for #{self.transcription_id}"


class FileAccess(models.Model):
    class Permission(models.TextChoices):
        VIEW = "view", "Просмотр"
        EDIT = "edit", "Редактирование"

    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name="accesses")
    user = models.ForeignKey("login.User", on_delete=models.CASCADE, related_name="file_accesses")
    permission = models.CharField(max_length=10, choices=Permission.choices, default=Permission.VIEW)

    class Meta:
        unique_together = ("file", "user")
        verbose_name = "Доступ к файлу"
        verbose_name_plural = "Доступы к файлам"

    def __str__(self) -> str:
        return f"{self.user.login} -> {self.file.name}: {self.permission}"


class RouteAccess(models.Model):
    class Access(models.TextChoices):
        USER = "u", "Только сотрудникам"
        ADMIN = "a", "Только администраторам"
        USER_AND_ADMIN = "ua", "И тем и тем"

    uri = models.CharField(max_length=255)
    method = models.CharField(max_length=16)
    access = models.CharField(max_length=2, choices=Access.choices, default=Access.USER_AND_ADMIN)

    class Meta:
        verbose_name = "Доступ к маршруту"
        verbose_name_plural = "Доступ к маршрутам"
        unique_together = ("uri", "method")

    def __str__(self) -> str:
        return f"{self.method} {self.uri}: {self.access}"