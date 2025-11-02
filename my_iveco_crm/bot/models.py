from django.db import models

class BotMessageLog(models.Model):
    chat_id = models.BigIntegerField(db_index=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    message_text = models.TextField(verbose_name="Повідомлення від користувача")
    bot_response = models.TextField(verbose_name="Відповідь бота")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час")

    class Meta:
        verbose_name = "Лог повідомлення"
        verbose_name_plural = "Логи повідомлень"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user_name} (ID: {self.chat_id}) - {self.created_at.strftime('%Y-%m-%d %H:%M')}"