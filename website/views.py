def home(request):
    from django.shortcuts import render
    return render(request, 'website/home.html')
