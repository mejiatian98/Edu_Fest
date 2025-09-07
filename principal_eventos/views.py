from app_admin_eventos.models import  Evento, Categoria, Area
from django.shortcuts import get_object_or_404, render, redirect
from django.views.generic import DetailView, ListView
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from django.utils.timezone import now
from django.contrib.auth.hashers import check_password
from app_usuarios.models import Usuario, Evaluador, Participante, AdministradorEvento, Asistente
from django.contrib.auth import authenticate, login, logout
from .decorador import visitor_required
from django.utils.decorators import method_decorator





    

######### LOGIN Y LOGOUT #########

def login_view(request):
    rol = request.session.get('rol')
    if rol == Usuario.Roles.ADMIN_EVENTO:
        return redirect('dashboard_admin')
    elif rol == Usuario.Roles.EVALUADOR:
        return redirect('dashboard_evaluador')
    elif rol == Usuario.Roles.PARTICIPANTE:
        return redirect('dashboard_participante')
    elif rol == Usuario.Roles.ASISTENTE:
        return redirect('dashboard_asistente')

    error = None

    if request.method == 'POST':
        identificador = request.POST.get('email_username')
        contrasena = request.POST.get('password')

        try:
            usuario_obj = Usuario.objects.get(Q(email=identificador) | Q(username=identificador))
        except Usuario.DoesNotExist:
            usuario_obj = None

        if usuario_obj:
            # 👉 Revisar antes si es primer acceso
            primer_acceso = usuario_obj.last_login is None

            user = authenticate(request, username=usuario_obj.username, password=contrasena)
            if user:
                login(request, user)
                user.is_active = True
                user.save(update_fields=["is_active"])
                # No necesitas guardar el rol si usas request.user.rol directamente


                # ADMIN
                if hasattr(user, 'administradorevento'):
                    request.session['admin_id'] = user.administradorevento.adm_id
                    request.session['admin_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_admin')
                    return redirect('dashboard_admin')


                # EVALUADOR
                elif hasattr(user, 'evaluador'):
                    request.session['evaluador_id'] = user.evaluador.eva_id
                    request.session['evaluador_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_evaluador')
                    return redirect('dashboard_evaluador')

                # PARTICIPANTE
                elif hasattr(user, 'participante'):
                    request.session['participante_id'] = user.participante.par_id
                    request.session['participante_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_participante')
                    return redirect('dashboard_participante')

                # ASISTENTE
                elif hasattr(user, 'asistente'):
                    request.session['asistente_id'] = user.asistente.asi_id
                    request.session['asistente_nombre'] = user.username
                    if primer_acceso:
                        return redirect('cambio_password_asistente')
                    return redirect('dashboard_asistente')

                else:
                    error = "Rol no reconocido."
            else:
                error = "Contraseña incorrecta."
        else:
            error = "Correo o nombre de usuario no encontrado."

    return render(request, 'login.html', {'error': error})




########### Logout ###########

def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect('pagina_principal')



########### VISTAS PRINCIPALES VISITANTES ###########
@method_decorator(visitor_required, name='dispatch')
class MenuPrincipalVisitanteView(ListView):
    model = Evento
    template_name = 'base.html'
    context_object_name = 'eventos'

    def get_queryset(self):
        today = now().date()

        # Actualizar eventos cuyo eve_fecha_fin es hoy y están en estado 'publicado'
        Evento.objects.filter(
            eve_estado__iexact='publicado',
            eve_fecha_fin=today
        ).update(eve_estado='Finalizado')

        # Filtrar eventos que están publicados o finalizados
        eventos = Evento.objects.filter(
            Q(eve_estado__iexact='publicado') | Q(eve_estado__iexact='Finalizado')
        ).order_by('-eve_fecha_inicio')

        # Filtros personalizados
        nombre = self.request.GET.get('nombre')
        ciudad = self.request.GET.get('ciudad')
        categoria_id = self.request.GET.get('categoria')
        area_id = self.request.GET.get('area')
        costo = self.request.GET.get('costo')
        estado = self.request.GET.get('estado')

        if nombre:
            eventos = eventos.filter(eve_nombre__icontains=nombre)
        if ciudad:
            eventos = eventos.filter(eve_ciudad__icontains=ciudad)
        if categoria_id:
            eventos = eventos.filter(categorias__id=categoria_id)
        if area_id:
            eventos = eventos.filter(categorias__cat_area_fk__id=area_id)
        if costo:
            eventos = eventos.filter(eve_tienecosto__iexact=costo)
        if estado:
            eventos = eventos.filter(eve_estado__iexact=estado)

        return eventos.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['areas'] = Area.objects.all()
        context['categorias'] = Categoria.objects.all()
        current_time = now().date()
        for evento in context['eventos']:
            if evento.eve_estado.lower() == 'Finalizado':
                evento.deletion_date = evento.eve_fecha_fin + timedelta(days=30)
        return context


########### VISTA DETALLE DE EVENTO ###########
@method_decorator(visitor_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento.html'
    context_object_name = 'evento'

@method_decorator(visitor_required, name='dispatch')
class EventoPreinscripcionesView(DetailView):
    model = Evento
    template_name = 'preinscripcion_eva_par.html'
    context_object_name = 'evento'







