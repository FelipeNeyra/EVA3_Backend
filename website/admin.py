from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Administrador, Cliente, Prestador


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        'idcliente',
        'nombre',
        'correo',
        'usuario',
        'nivel_acceso',
    )
    search_fields = (
        'nombre',
        'correo',
        'usuario__username',
        'usuario__email',
    )


@admin.register(Prestador)
class PrestadorAdmin(admin.ModelAdmin):
    list_display = (
        'idprestador',
        'usuario',
        'especialidad',
        'estado_aprobacion',
        'nivel_acceso',
    )
    search_fields = (
        'usuario__username',
        'usuario__email',
        'especialidad',
    )
    list_filter = ('estado_aprobacion', 'nivel_acceso')


@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ('idadministrador', 'usuario', 'nivel_acceso')
    search_fields = ('usuario__username', 'usuario__email')


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
