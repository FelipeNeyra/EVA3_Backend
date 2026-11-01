"""
URL configuration for gestion_citas_rgbeauty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from website.views import home
from website import views as vistas
#Librería de Vistas de Autenticación
from django.contrib.auth import views as auth_views
from website.forms import CorreoAuthenticationForm

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),

    #Registro y Login
    path('registro/', vistas.vista_registro, name='registro'),
    path('login/',
        auth_views.LoginView.as_view(
            template_name='website/login.html',
            authentication_form=CorreoAuthenticationForm,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    #Datos de cuenta y cambio de contraseña
    path('home/datos_cuenta', vistas.vista_editar_informacion_usuario, name='datos_usuario'),
    path('cambiar_contraseña/', auth_views.PasswordChangeView.as_view(
        template_name='website/cuenta/cambiar_contraseña.html'), 
        name='password_change'),
    path('cambiar_contraseña/hecho', auth_views.PasswordChangeDoneView.as_view(
        template_name='website/cuenta/cambiar_contraseña_hecho.html'), 
        name='password_change_done'),

    #Sección de Prestadores
    path('home/solicitudes', vistas.vista_solicitud_prestadores, name='solicitud_prestador'),

     #Sección de Administración
    path('administración/', vistas.vista_administrador, name='vista_administrador'),
    path('administración/<int:pk>/estado/', vistas.vista_aprobar_rechazar_solicitud, name='estado_solicitud'),

]
