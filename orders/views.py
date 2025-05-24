from django.http import HttpResponse
from django.views import View

class RollbarTestView(View):
    def get(self, request):
        # Пример ошибки для тестирования Rollbar
        try:
            a = None
            a.hello()  # Это вызовет ошибку
        except Exception as e:
            # Логируем ошибку в Rollbar
            import rollbar
            rollbar.report_exc_info()
            return HttpResponse(f"Error: {str(e)}", status=500)
        
        return HttpResponse("Test view")
