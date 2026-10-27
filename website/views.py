from django.shortcuts import redirect, render
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .forms import RegistroForm, RegistroClienteForm, RegistroPrestadorForm
from django.contrib import messages

#Vista Principal
def home(request):
    return render(request, 'website/home.html')

#Vista de Formulario de Registro (Usuario_Cliente)
def vista_registro(request):
    user_form = RegistroForm(request.POST or None)
    cliente_form = RegistroClienteForm(request.POST or None)

    if request.method == 'POST':
        if user_form.is_valid() and cliente_form.is_valid():
            with transaction.atomic():
                user = user_form.save()
                cliente = cliente_form.save(commit=False)
                cliente.usuario = user
                cliente.correo = user.email
                cliente.save()
            login(request, user)
            return redirect('home')

    return render(
        request,
        'website/registro.html',
        {
            'user_form': user_form,
            'cliente_form': cliente_form,
        },
    )

#Vista de Solicitud para Prestadores
@login_required
def vista_solicitud_prestadores(request):
    prestador_form = RegistroPrestadorForm(request.POST or None)

    if request.method == 'POST':
        if prestador_form.is_valid():
            current_user = request.user

            if hasattr(request.user, 'perfil_prestador'):
                messages.success(request, f'Ya tienes una solicitud envíada y en estado de evaluación')
                return redirect('home')
            prestador = prestador_form.save(commit=False)
            prestador.usuario = current_user
            prestador.save()
            return redirect('home')

    return render(
        request,
        'website/solicitud_prestador.html',
        {
            'prestador_form': prestador_form
        },
    )
