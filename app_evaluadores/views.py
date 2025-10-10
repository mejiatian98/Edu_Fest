from typing import Counter
from django.utils.timezone import now
from django.utils import timezone
import re
from django.contrib import messages
from django.shortcuts import render
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.core.mail import send_mail
from app_participantes.models import ParticipanteEvento
from app_usuarios.models import Evaluador, Participante, Usuario
from principal_eventos.settings import DEFAULT_FROM_EMAIL
from .models import Calificacion, EvaluadorEvento
from app_admin_eventos.models import Area, Categoria, Criterio, Evento
from .forms import EvaluadorForm, EditarUsuarioEvaluadorForm
from django.views.generic import DetailView, ListView
from django.db.models import Q
from django.db.models import Exists, OuterRef
from django.utils.timezone import now, localtime
import random
import string
from django.contrib.auth.hashers import make_password , check_password
from django.utils.decorators import method_decorator
from principal_eventos.decorador import evaluador_required, visitor_required
from django.db import models
from django.db.models import Q, Sum
from django.contrib.auth.decorators import login_required
from app_admin_eventos.models import Evento, MemoriaEvento
from django.conf import settings



########### VISTA DEL DASHBOARD DEL EVALUADOR ###########
@method_decorator(evaluador_required, name='dispatch')
class DashboardEvaluadorView(View):
    def get(self, request):
        evaluador_id = request.session.get('evaluador_id')
        if not evaluador_id:
            messages.error(request, "Debe iniciar sesión como evaluador.")
            return redirect('login_view')

        try:
            evaluador = Evaluador.objects.get(id=evaluador_id)
        except Evaluador.DoesNotExist:
            messages.error(request, "Evaluador no encontrado.")
            return redirect('login_view')

        # Relación completa con estado
        relaciones = EvaluadorEvento.objects.filter(eva_eve_evaluador_fk=evaluador).select_related('eva_eve_evento_fk')

        # Separar eventos según estado
        eventos_aprobados = [rel.eva_eve_evento_fk for rel in relaciones if rel.eva_eve_estado == 'Aprobado']
        eventos_pendientes = [rel.eva_eve_evento_fk for rel in relaciones if rel.eva_eve_estado == 'Pendiente']

        # Aplicar filtros sobre eventos_aprobados
        nombre = request.GET.get('nombre')
        ciudad = request.GET.get('ciudad')
        area_id = request.GET.get('area')
        categoria_id = request.GET.get('categoria')
        costo = request.GET.get('costo')
        estado = request.GET.get('estado')

        eventos = Evento.objects.filter(id__in=[e.id for e in eventos_aprobados])

        if nombre:
            eventos = eventos.filter(eve_nombre__icontains=nombre)
        if ciudad:
            eventos = eventos.filter(eve_lugar__icontains=ciudad)
        if area_id:
            eventos = eventos.filter(categorias__cat_area_fk__id=area_id).distinct()
        if categoria_id:
            eventos = eventos.filter(categorias__id=categoria_id).distinct()
        if costo:
            eventos = eventos.filter(eve_costo=costo)
        if estado:
            eventos = eventos.filter(eve_estado=estado)

        # Verificar si los criterios suman 100 para habilitar botón
        criterios_completos = {}
        for evento in eventos:
            suma_pesos = Criterio.objects.filter(cri_evento_fk=evento).aggregate(total=models.Sum('cri_peso'))['total'] or 0
            criterios_completos[evento.id] = (suma_pesos == 100)

        context = {
            'evaluador': evaluador,
            'eventos': eventos,
            'eventos_pendientes': eventos_pendientes,
            'areas': Area.objects.all(),
            'categorias': Categoria.objects.all(),
            'criterios_completos': criterios_completos,
        }
        return render(request, 'dashboard_principal_evaluador.html', context)

    #Iniciar sesion una vez y cambiar contraseña
    def dispatch(self, request, *args, **kwargs):
        evaluador_id = request.session.get('evaluador_id')
        evaluador = get_object_or_404(Evaluador, pk=evaluador_id)

        # Si nunca ha iniciado sesión, forzar cambio de contraseña
        if not evaluador.usuario.last_login:
            return redirect('cambio_password_evaluador')

        return super().dispatch(request, *args, **kwargs)


##################### --- Cambio de Contraseña Evaluador --- #####################

@method_decorator(evaluador_required, name='dispatch')
class CambioPasswordEvaluadorView(View):
    template_name = 'cambio_password_evaluador.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "❌ Las contraseñas no coinciden.")
            return render(request, self.template_name)

        if len(password1) < 6:
            messages.error(request, "❌ La contraseña debe tener al menos 6 caracteres.")
            return render(request, self.template_name)

        evaluador_id = request.session.get('evaluador_id')
        evaluador = get_object_or_404(Evaluador, pk=evaluador_id)
        usuario = evaluador.usuario

        usuario.set_password(password1)
        usuario.ultimo_acceso = timezone.now()  # ✅ Se actualiza solo aquí
        usuario.save()

        messages.success(request, "✅ Contraseña cambiada correctamente.")
        return redirect('dashboard_evaluador')


########### CREAR EVALUADOR ###########

@method_decorator(visitor_required, name='dispatch')
class EvaluadorCreateView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        form = EvaluadorForm()
        return render(request, 'crear_evaluador.html', {
            'form': form,
            'evento': evento
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        form = EvaluadorForm(request.POST, request.FILES, evento=evento)

        if form.is_valid():
            cedula = form.cleaned_data['cedula']
            username = form.cleaned_data['username']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            telefono = form.cleaned_data['telefono']

            documento = request.FILES.get('eva_eve_documento')

            # 🔹 Verificar si ya existe el usuario
            usuario, creado = Usuario.objects.get_or_create(
                email=email,
                defaults={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "telefono": telefono,
                    "is_superuser": False,
                    "is_staff": False,
                    "is_active": True,
                    "date_joined": localtime(now()),
                    "rol": "EVALUADOR",
                    "password": make_password(''.join(random.choices(string.ascii_letters + string.digits, k=20)))
                }
            )

            if creado:
                # Usuario nuevo → generar contraseña
                password_plana = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                usuario.password = make_password(password_plana)
                usuario.save()
            else:
                # Usuario ya existe → usa su contraseña actual
                password_plana = None

            # 🔹 Verificar si ya existe un Evaluador con ese usuario
            evaluador, evaluador_creado = Evaluador.objects.get_or_create(usuario=usuario)

            if evaluador_creado:
                # ✅ Solo asignamos la cédula, el ID se autogenera
                evaluador.cedula = cedula
                evaluador.save(update_fields=["cedula"])
            else:
                # Si el evaluador ya existe, verificar que la cédula coincida
                if evaluador.cedula != cedula:
                    messages.error(request, "La cédula ingresada no coincide con el evaluador registrado.")
                    return render(request, 'crear_evaluador.html', {'form': form, 'evento': evento})

            # 🔹 Verificar si ya está inscrito en este evento (permitir otros eventos)
            if EvaluadorEvento.objects.filter(
                eva_eve_evaluador_fk=evaluador,
                eva_eve_evento_fk=evento
            ).exists():
                messages.warning(request, "Este evaluador ya está registrado en este evento.")
                return redirect('pagina_principal')

            # 🔹 Crear relación EvaluadorEvento
            EvaluadorEvento.objects.create(
                eva_eve_evaluador_fk=evaluador,
                eva_eve_evento_fk=evento,
                eva_eve_fecha_hora=now(),
                eva_eve_estado="Pendiente",
                eva_eve_documento=documento
            )

            # 🔹 Enviar correo (diferente según si el usuario es nuevo o no)
            try:
                if creado:
                    mensaje = (
                        f"Hola Evaluador {usuario.first_name},\n\n"
                        f"Te has registrado correctamente al evento \"{evento.eve_nombre}\".\n"
                        f"Tu estado actual es 'Pendiente' y será revisado por el administrador del evento.\n\n"
                        f"Puedes iniciar sesión con las siguientes credenciales:\n"
                        f"Correo registrado: {usuario.email}\n"
                        f"Contraseña generada: {password_plana}\n\n"
                        f"Recomendamos cambiar tu contraseña después de iniciar sesión.\n\n"
                        f"Atentamente,\nEquipo Event-Soft"
                    )
                else:
                    mensaje = (
                        f"Hola Evaluador {usuario.first_name},\n\n"
                        f"Te has inscrito correctamente al evento \"{evento.eve_nombre}\".\n"
                        f"Tu estado actual es 'Pendiente' y será revisado por el administrador del evento.\n\n"
                        f"Recuerda que debes iniciar sesión con tu correo: {usuario.email}\n"
                        f"y tu contraseña actual (la misma que ya usas en Event-Soft).\n\n"
                        f"Atentamente,\nEquipo Event-Soft"
                    )

                send_mail(
                    subject=f"🎟️ Datos de acceso - Evento \"{evento.eve_nombre}\"",
                    message=mensaje,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[usuario.email],
                    fail_silently=False
                )
            except Exception as e:
                messages.warning(request, f"Usuario registrado, pero no se pudo enviar el correo: {e}")

            messages.success(
                request,
                f"Evaluador registrado correctamente al evento '{evento.eve_nombre}'."
            )
            return redirect('pagina_principal')

        else:
            messages.error(request, "Corrija los errores en el formulario.")

        return render(request, 'crear_evaluador.html', {
            'form': form,
            'evento': evento
        })


######### EDITAR EVALUADOR ##########

@method_decorator(evaluador_required, name='dispatch')
class EditarEvaluadorView(View):
    template_name = 'editar_evaluador.html'

    def get(self, request, evaluador_id):
        evaluador = get_object_or_404(Evaluador, id=evaluador_id)
        usuario = evaluador.usuario
        form = EditarUsuarioEvaluadorForm(instance=usuario)

        # Traer todas las relaciones del evaluador con los eventos
        todas_relaciones = EvaluadorEvento.objects.filter(
            eva_eve_evaluador_fk=evaluador
        ).select_related("eva_eve_evento_fk")

        return render(request, self.template_name, {
            'form': form,
            'evaluador': evaluador,
            'usuario': usuario,
            'todas_relaciones': todas_relaciones
        })

    def post(self, request, evaluador_id):
        evaluador = get_object_or_404(Evaluador, id=evaluador_id)
        usuario = evaluador.usuario
        form = EditarUsuarioEvaluadorForm(request.POST, request.FILES, instance=usuario)

        nueva_contrasena = request.POST.get('nueva_contrasena')
        confirmar_contrasena = request.POST.get('confirmar_contrasena')
        confirmar_contrasena_nueva = request.POST.get('confirmar_contrasena_nueva')

        if form.is_valid():
            # 🔹 Verificar y actualizar contraseña
            if nueva_contrasena and confirmar_contrasena and confirmar_contrasena_nueva:
                if not check_password(nueva_contrasena, usuario.password):
                    messages.error(request, "❌ La contraseña antigua no es correcta.")
                    return self.get(request, evaluador_id)

                if confirmar_contrasena != confirmar_contrasena_nueva:
                    messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                    return self.get(request, evaluador_id)

                if len(confirmar_contrasena) < 6:
                    messages.error(request, "❌ La nueva contraseña debe tener al menos 6 caracteres.")
                    return self.get(request, evaluador_id)

                usuario.set_password(confirmar_contrasena)

            # ✅ Guardar documentos subidos (revisar por cada relación)
            todas_relaciones = EvaluadorEvento.objects.filter(eva_eve_evaluador_fk=evaluador)
            for relacion in todas_relaciones:
                input_name = f"eva_eve_documento_{relacion.id}"
                if input_name in request.FILES:
                    documento = request.FILES[input_name]
                    if not documento.name.lower().endswith('.pdf'):
                        messages.error(request, f"❌ El documento para {relacion.eva_eve_evento_fk.eve_nombre} debe ser un PDF.")
                        return self.get(request, evaluador_id)

                    relacion.eva_eve_documento = documento
                    relacion.save()

            # ✅ Guardar datos del usuario
            form.save()
            usuario.save()

            messages.success(request, "✅ Los datos del evaluador y documentos se actualizaron correctamente.")
            return redirect('editar_evaluador', evaluador_id=evaluador_id)

        else:
            messages.error(request, "❌ No se pudo guardar. Revisa los errores del formulario.")
            return self.get(request, evaluador_id)





########### VER INFORMACIÓN EVENTO ###########
@method_decorator(evaluador_required, name='dispatch')
class EventoDetailView(DetailView):
    model = Evento
    template_name = 'info_evento_evento_eva.html'
    context_object_name = 'evento'
    pk_url_kwarg = 'pk'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento = self.get_object()
        evaluador_id = self.request.session.get('evaluador_id')
        
        # Verificar si el evaluador está asignado a este evento
        if evaluador_id:
            evaluador = get_object_or_404(Evaluador, id=evaluador_id)
            if not EvaluadorEvento.objects.filter(eva_eve_evaluador_fk=evaluador, eva_eve_evento_fk=evento).exists():
                messages.error(self.request, "No tienes permiso para ver este evento.")
                return redirect('pagina_principal')

        context['evaluador'] = evaluador if evaluador_id else None
        return context


######## VER CRITERIOS DE EVALUACIÓN #########
@method_decorator(evaluador_required, name='dispatch')
class CriterioEvaListView(ListView):
    model = Criterio
    template_name = 'crear_criterios_evaluacion_eva.html'
    context_object_name = 'criterios'

    def get_queryset(self):
        evento_id = self.kwargs.get('evento_id')
        return Criterio.objects.filter(cri_evento_fk__id=evento_id).order_by('cri_descripcion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs.get('evento_id')
        evento = get_object_or_404(Evento, id=evento_id)
        criterios = context['criterios']  # queryset con criterios filtrados

        suma_pesos = sum(criterio.cri_peso for criterio in criterios)
        context['evento'] = evento
        context['suma_pesos'] = round(suma_pesos, 2)

        # Validación para saber si ya están completos los 100 puntos
        context['completo_100'] = (suma_pesos == 100)

        return context
 
@method_decorator(evaluador_required, name='dispatch')
class CrearCriterioEvaView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        suma_pesos = sum(criterio.cri_peso for criterio in criterios)

        return render(request, 'crear_criterios_evaluacion_eva.html', {
            'evento': evento,
            'criterios': criterios,
            'suma_pesos': round(suma_pesos, 2),
        })

    def post(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        descripcion = request.POST.get('cri_descripcion')
        peso_str = request.POST.get('cri_peso')

        # Validar campos vacíos
        if not descripcion or not peso_str:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('crear_criterio_eva', evento_id=evento_id)

        # Intentar convertir el peso a float
        try:
            peso = float(peso_str)
        except ValueError:
            messages.error(request, 'El peso debe ser un número válido.')
            return redirect('crear_criterio_eva', evento_id=evento_id)

        # Obtener los criterios existentes y su suma de pesos
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        suma_pesos = sum(criterio.cri_peso for criterio in criterios)

        # Validar si ya se alcanzó el máximo
        if suma_pesos >= 100:
            messages.error(request, 'La suma de los pesos ya llegó a 100%. No se pueden agregar más criterios.')
            return redirect('crear_criterio_eva', evento_id=evento_id)

        # Validar que la suma con el nuevo peso no exceda 100
        if suma_pesos + peso > 100:
            messages.error(
                request,
                f'La suma de los pesos no puede superar 100%. Actualmente hay {round(suma_pesos, 2)}%.'
            )
            return redirect('crear_criterio_eva', evento_id=evento_id)

        # Crear el nuevo criterio
        Criterio.objects.create(
            cri_descripcion=descripcion,
            cri_peso=peso,
            cri_evento_fk=evento
        )

        messages.success(request, 'Criterio creado exitosamente.')
        return redirect('crear_criterio_eva', evento_id=evento_id)

@method_decorator(evaluador_required, name='dispatch')
class ActualizarEvaCriterioView(View):
    def post(self, request, criterio_id):
        criterio = get_object_or_404(Criterio, pk=criterio_id)
        descripcion = request.POST.get('cri_descripcion')
        peso_str = request.POST.get('cri_peso')

        if not descripcion or not peso_str:
            messages.error(request, 'Todos los campos son obligatorios.')
            return redirect('crear_criterio_eva', evento_id=criterio.cri_evento_fk.id)

        try:
            nuevo_peso = float(peso_str)
        except ValueError:
            messages.error(request, 'El peso debe ser un número válido.')
            return redirect('crear_criterio_eva', evento_id=criterio.cri_evento_fk.id)

        # Obtener criterios del mismo evento excepto el que se está actualizando
        criterios = Criterio.objects.filter(cri_evento_fk=criterio.cri_evento_fk).exclude(pk=criterio.pk)
        suma_pesos_otros = sum(c.cri_peso for c in criterios)

        # Validar suma total con nuevo peso
        if suma_pesos_otros + nuevo_peso > 100:
            messages.error(
                request,
                f'La suma total de pesos no puede superar 100%. Actualmente hay {round(suma_pesos_otros, 2)}%.'
            )
            return redirect('crear_criterio_eva', evento_id=criterio.cri_evento_fk.id)

        # Guardar si pasa validación
        criterio.cri_descripcion = descripcion
        criterio.cri_peso = nuevo_peso
        criterio.save()

        messages.success(request, 'Criterio actualizado exitosamente.')
        return redirect('crear_criterio_eva', evento_id=criterio.cri_evento_fk.id)
    

@method_decorator(evaluador_required, name='dispatch')
class EliminarEvaCriterioView(View):
    def post(self, request, criterio_id):
        criterio = get_object_or_404(Criterio, pk=criterio_id)
        evento_id = criterio.cri_evento_fk.id
        criterio.delete()

        messages.success(request, 'Criterio eliminado exitosamente.')
        return redirect('crear_criterio_eva', evento_id=evento_id)
    
@method_decorator(evaluador_required, name='dispatch')
class CriterioAgregadosEvaListView(ListView):
    model = Criterio
    template_name = 'ver_criterios_evaluador_eva.html'
    context_object_name = 'criterios'

    def get_queryset(self):
        evento_id = self.kwargs.get('evento_id')
        return Criterio.objects.filter(cri_evento_fk__id=evento_id).order_by('cri_descripcion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs.get('evento_id')
        context['evento'] = get_object_or_404(Evento, id=evento_id)
        return context
    

############ CALIFICAR PARTICIPANTES MODIFICADO PARA GRUPOS ###########

@method_decorator(evaluador_required, name='dispatch')
class CalificarParticipantesView(View):
    template_name = 'ver_lista_participantes.html'

    def get(self, request, evento_id):
        evaluador = get_object_or_404(Evaluador, id=request.session['evaluador_id'])
        evento = get_object_or_404(Evento, pk=evento_id)

        # Obtener los criterios del evento (para luego filtrar calificaciones)
        criterios = Criterio.objects.filter(cri_evento_fk=evento)

        # Participantes en el evento, solo aquellos con estado 'aprobado'
        # Solo mostrar líderes de grupo o participantes individuales
        participantes_evento = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento_id,
            par_eve_estado='Aprobado',
            par_eve_proyecto_principal__isnull=True  # Solo líderes o individuales
        )

        # Filtro por nombre o cédula
        filtro = request.GET.get('filtro')
        if filtro:
            participantes_evento = participantes_evento.filter(
                Q(par_eve_participante_fk__usuario__first_name__icontains=filtro) |
                Q(par_eve_participante_fk__usuario__email__icontains=filtro) |
                Q(par_eve_participante_fk__usuario__last_name__icontains=filtro)
            )

        # Excluir participantes que ya tienen calificaciones para los criterios del evento
        # Para grupos, verificar si el líder ya fue calificado
        calificados = Calificacion.objects.filter(
            cal_evaluador_fk=evaluador,
            cal_participante_fk=OuterRef('par_eve_participante_fk'),
            cal_criterio_fk__in=criterios
        )

        participantes_evento = participantes_evento.annotate(
            ya_calificado=Exists(calificados)
        ).filter(ya_calificado=False)

        # Lista de participantes que aún no han sido calificados
        participantes = [pe.par_eve_participante_fk for pe in participantes_evento]

        return render(request, self.template_name, {
            'participantes': participantes,
            'evento_id': evento_id,
            'evento': evento,
            'evaluador': evaluador
        })


@method_decorator(evaluador_required, name='dispatch')
class CalificandoParticipanteView(View):
    def get(self, request, participante_id, evento_id):
        participante = get_object_or_404(Participante, pk=participante_id)
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        
        # Obtener la relación ParticipanteEvento del participante
        participante_evento = get_object_or_404(ParticipanteEvento, 
                                               par_eve_participante_fk=participante,
                                               par_eve_evento_fk=evento,
                                               par_eve_proyecto_principal__isnull=True)  # Solo líderes
        
        # Verificar si es un grupo y obtener todos los miembros
        miembros_grupo = []
        es_grupo = participante_evento.par_eve_es_grupo
        
        if es_grupo:
            # Obtener todos los miembros del grupo (incluyendo el líder)
            todos_miembros = participante_evento.get_todos_miembros_proyecto()
            miembros_grupo = todos_miembros
        else:
            # Si es individual, solo incluir al participante
            miembros_grupo = [participante_evento]

        return render(request, 'evaluador_califica_participante.html', {
            'participante': participante,
            'evento': evento,
            'criterios': criterios,
            'es_grupo': es_grupo,
            'miembros_grupo': miembros_grupo,
            'participante_evento': participante_evento,
            'codigo_proyecto': participante_evento.par_eve_codigo_proyecto if es_grupo else None
        })

    def post(self, request, participante_id, evento_id):
        participante = get_object_or_404(Participante, pk=participante_id)
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento)
        evaluador_id = request.session.get('evaluador_id')
        evaluador = get_object_or_404(Evaluador, pk=evaluador_id)

        # Obtener la relación ParticipanteEvento del líder
        participante_evento_lider = get_object_or_404(ParticipanteEvento, 
                                                     par_eve_participante_fk=participante,
                                                     par_eve_evento_fk=evento,
                                                     par_eve_proyecto_principal__isnull=True)

        # Lista para almacenar las calificaciones obtenidas
        calificaciones = []

        # Guardar las calificaciones de cada criterio para el líder
        for criterio in criterios:
            campo = f'calificacion_{criterio.id}'
            valor = request.POST.get(campo)
            if valor:
                calificaciones.append(int(valor))
                
                # Guardamos la calificación solo para el líder
                Calificacion.objects.update_or_create(
                    cal_evaluador_fk=evaluador,
                    cal_criterio_fk=criterio,
                    cal_participante_fk=participante,
                    defaults={'cal_valor': int(valor)}
                )

        # Calcular promedio de las calificaciones actuales
        if calificaciones:
            promedio = sum(calificaciones) / len(calificaciones)
            calificacion_final = round(promedio)
            
            # Aplicar la calificación a todo el grupo
            if participante_evento_lider.par_eve_es_grupo:
                # Obtener todos los miembros del proyecto (incluido el líder)
                todos_miembros = participante_evento_lider.get_todos_miembros_proyecto()
                
                for miembro_pe in todos_miembros:
                    miembro_pe.calificacion = calificacion_final
                    miembro_pe.save()
                
                # Crear registro de calificación para todos los miembros (para tracking)
                for miembro_pe in todos_miembros:
                    if miembro_pe.par_eve_participante_fk != participante:  # Evitar duplicar para el líder
                        for criterio in criterios:
                            campo = f'calificacion_{criterio.id}'
                            valor = request.POST.get(campo)
                            if valor:
                                Calificacion.objects.update_or_create(
                                    cal_evaluador_fk=evaluador,
                                    cal_criterio_fk=criterio,
                                    cal_participante_fk=miembro_pe.par_eve_participante_fk,
                                    defaults={'cal_valor': int(valor)}
                                )
                
                mensaje_exito = f"Calificaciones para el grupo de {participante.usuario.first_name} {participante.usuario.last_name} guardadas correctamente. La calificación se aplicó a todos los {len(todos_miembros)} miembros del grupo."
            else:
                # Participante individual
                participante_evento_lider.calificacion = calificacion_final
                participante_evento_lider.save()
                mensaje_exito = f"Calificaciones para {participante.usuario.first_name} {participante.usuario.last_name} guardadas correctamente."

            messages.success(request, mensaje_exito)
        else:
            messages.error(request, "No se pudieron guardar las calificaciones. Verifique los valores ingresados.")

        return redirect('calificar_participantes', evento_id=evento_id)


# Función auxiliar para obtener información de grupo (opcional)
def obtener_info_grupo_participante(participante, evento):
    """
    Función auxiliar que devuelve información sobre si un participante pertenece a un grupo
    """
    try:
        participante_evento = ParticipanteEvento.objects.get(
            par_eve_participante_fk=participante,
            par_eve_evento_fk=evento
        )
        
        if participante_evento.par_eve_proyecto_principal:
            # Es miembro de un grupo, obtener info del líder
            lider_pe = participante_evento.par_eve_proyecto_principal
            return {
                'es_miembro_grupo': True,
                'es_lider': False,
                'lider': lider_pe.par_eve_participante_fk,
                'codigo_proyecto': lider_pe.par_eve_codigo_proyecto,
                'participante_evento': participante_evento
            }
        elif participante_evento.par_eve_es_grupo:
            # Es líder de grupo
            miembros = participante_evento.get_todos_miembros_proyecto()
            return {
                'es_miembro_grupo': True,
                'es_lider': True,
                'miembros': miembros,
                'codigo_proyecto': participante_evento.par_eve_codigo_proyecto,
                'participante_evento': participante_evento
            }
        else:
            # Participante individual
            return {
                'es_miembro_grupo': False,
                'es_lider': False,
                'participante_evento': participante_evento
            }
    except ParticipanteEvento.DoesNotExist:
        return None




################## VER PODIO ################
@method_decorator(evaluador_required, name='dispatch')
class VerPodioParticipantesView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        evaluador = get_object_or_404(Evaluador, id=request.session['evaluador_id'])

        participantes_evento = ParticipanteEvento.objects.filter(
            par_eve_evento_fk=evento_id,
            calificacion__isnull=False
        ).select_related('par_eve_participante_fk')

        participantes_calificados = []
        for pe in participantes_evento:
            participante = pe.par_eve_participante_fk
            if participante and participante.id:
                pe.participante = participante

                # Extraer primer nombre y apellido
                first_name = participante.usuario.first_name.split()[0].upper()
                last_name = participante.usuario.last_name.split()[0].upper()

                # Guardar como atributos personalizados
                pe.nombre_limpio = first_name
                pe.apellido_limpio = last_name

                participantes_calificados.append(pe)


        participantes_calificados.sort(key=lambda x: x.calificacion, reverse=True)

        return render(request, 'ver_notas_participantes.html', {
            'participantes': participantes_calificados,
            'evento': evento,
            'evaluador': evaluador
        })



########## VER NOTAS DE PARTICIPANTES #########

@method_decorator(evaluador_required, name='dispatch')
class DetalleCalificacionView(DetailView):
    template_name = 'ver_detalle_calificacion_podio.html'
    context_object_name = 'participante'
    model = Participante

    def get_object(self):
        return get_object_or_404(Participante, id=self.kwargs['participante_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        evento_id = self.kwargs['evento_id']
        participante = self.get_object()
        evento = get_object_or_404(Evento, id=evento_id)

        participante_evento = get_object_or_404(
            ParticipanteEvento,
            par_eve_evento_fk=evento,
            par_eve_participante_fk=participante
        )

        calificaciones = Calificacion.objects.filter(
            cal_participante_fk=participante,
            cal_criterio_fk__cri_evento_fk=evento
        ).select_related('cal_criterio_fk', 'cal_evaluador_fk')

        context.update({
            'evento': evento,
            'participante_evento': participante_evento,
            'calificaciones': calificaciones,
        })

        return context


######### ELIMINAR EVALUADOR #########

@method_decorator(evaluador_required, name='dispatch')
class EliminarEvaluadorView(View):
    def get(self, request, evaluador_id):
        evaluador = get_object_or_404(Evaluador, id=evaluador_id)
        usuario = evaluador.usuario

        # Obtener el evento asignado, si lo hay
        evaluador_evento = EvaluadorEvento.objects.filter(eva_eve_evaluador_fk=evaluador).first()
        nombre_evento = evaluador_evento.eva_eve_evento_fk.eve_nombre if evaluador_evento else "uno de nuestros eventos"

        # Enviar correo antes de eliminar
        if usuario.email:
            send_mail(
                subject='Notificación de eliminación de cuenta como evaluador',
                message=(
                    f'Estimado/a {usuario.last_name},\n\n'
                    f'Le informamos que ha sido eliminado como evaluador del evento "{nombre_evento}". '
                    f'Todos sus datos han sido eliminados por razones de seguridad.\n\n'
                    f'Si tiene preguntas o requiere mayor información, no dude en contactarnos.\n\n'
                    f'Atentamente,\nEquipo de organización de eventos.'
                ),
                from_email=DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False
            )

        # Cerrar sesión antes de eliminar
        request.session.flush()

        # Eliminar al usuario (esto elimina automáticamente al evaluador)
        usuario.delete()

        messages.success(request, "El evaluador ha sido eliminado correctamente.")
        return redirect('pagina_principal')

    
    
######### LISTADO DE PARTICIPANTES ##########

@method_decorator(evaluador_required, name='dispatch')
class ListadoParticipantesPorEventoView(View):
    template_name = 'listado_participantes.html'

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)

        # Todos los participantes del evento (para contar todos los estados)
        todos_los_participantes = ParticipanteEvento.objects.filter(par_eve_evento_fk=evento)

        # Conteo por estado
        estados = todos_los_participantes.values_list('par_eve_estado', flat=True)
        conteo = Counter(estados)

        # Solo participantes Aprobados (para mostrar)
        participantes_evento = todos_los_participantes.filter(par_eve_estado='Aprobado')

        # Filtro por búsqueda si se aplica
        query = request.GET.get('q')
        if query:
            participantes_evento = participantes_evento.filter(
                Q(par_eve_participante_fk__usuario__first_name__icontains=query) |
                Q(par_eve_participante_fk__usuario__last_name__icontains=query) |
                Q(par_eve_participante_fk__id__icontains=query)
            )

        participantes = []
        for p in participantes_evento:
            participantes.append({
                'cedula': p.par_eve_participante_fk.id,
                'nombre': p.par_eve_participante_fk.usuario.first_name,
                'apellido': p.par_eve_participante_fk.usuario.last_name,
                'correo': p.par_eve_participante_fk.usuario.email,
                'telefono': p.par_eve_participante_fk.usuario.telefono,
                'par_eve_estado': p.par_eve_estado,
                'documento_url': p.par_eve_documentos.url if p.par_eve_documentos else None
            })

        return render(request, self.template_name, {
            'evento': evento,
            'participantes': participantes,
            'query': query,
            'conteo_aprobados': conteo.get('Aprobado', 0),
            'conteo_pendientes': conteo.get('Pendiente', 0),
            'conteo_rechazados': conteo.get('Rechazado', 0),
        })


######### RÚBRICA DEL EVENTO ##########

@method_decorator(evaluador_required, name='dispatch')
class InformacionTecnicaEventoEvaluadorView(View):
    template_name = 'info_tecnica_evento_eva.html'

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        return render(request, self.template_name, {'evento': evento})

    def post(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)

        if 'informacion_tecnica' in request.FILES:
            archivo = request.FILES['informacion_tecnica']
            evento.eve_informacion_tecnica = archivo
            evento.save()
            messages.success(request, "Archivo subido correctamente.")
        else:
            messages.warning(request, "Por favor selecciona un archivo.")

        return redirect('ver_info_tecnica_evento', pk=pk)


####### ACCESO A EVENTO ######
@method_decorator(evaluador_required, name='dispatch')
class IngresoEventoEvaluadorView(View):
    template_name = 'ingreso_evento_eva.html'

    def get(self, request, pk):
        evento = get_object_or_404(Evento, pk=pk)
        evaluador = get_object_or_404(Evaluador, usuario=request.user)
        evaluador_evento = get_object_or_404(EvaluadorEvento, eva_eve_evento_fk=evento, eva_eve_evaluador_fk=evaluador)

        context = {
            'evento': evento,
            'evaluador': evaluador_evento  # este es el objeto que tiene el QR y el soporte
        }
        return render(request, self.template_name, context)
  
########## VER CRITERIOS DE EVALUACIÓN PARA PARTICIPANTES #########
@method_decorator(evaluador_required, name='dispatch')
class VerCriteriosEvaluadorView(View):
    template_name = 'ver_criterios_eva.html'

    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, pk=evento_id)
        criterios = Criterio.objects.filter(cri_evento_fk=evento).order_by('cri_descripcion')
        evaluador = get_object_or_404(Evaluador, id=request.session['evaluador_id'])

        return render(request, self.template_name, {
            'evento': evento,
            'criterios': criterios,
            'evaluador': evaluador,
        })




################ #### VER MEMORIAS DE EVALUADOR ##########
@method_decorator(login_required, name='dispatch')
class MemoriasEvaluadorView(View):
    def get(self, request, evento_id):
        evento = get_object_or_404(Evento, id=evento_id)
        # Verificar inscripción como evaluador
        inscrito = EvaluadorEvento.objects.filter(
            eva_eve_evento_fk=evento,
            eva_eve_evaluador_fk__usuario=request.user
        ).exists()
        if not inscrito:
            messages.error(request, "❌ No estás inscrito como evaluador en este evento.")
            return redirect('dashboard_user')
        memorias = MemoriaEvento.objects.filter(evento=evento).order_by('-subido_en')
        return render(request, 'memorias_evaluador.html', {'evento': evento, 'memorias': memorias})


########## CANCELAR INSCRIPCIÓN AL EVENTO ##########


@method_decorator(login_required, name='dispatch')
class EvaluadorCancelacionView(View):
    def post(self, request, evento_id):
        evaluador = get_object_or_404(Evaluador, usuario=request.user)
        evento = get_object_or_404(Evento, id=evento_id)

        # Buscar inscripción activa del evaluador en este evento
        inscripcion = EvaluadorEvento.objects.filter(
            eva_eve_evaluador_fk=evaluador,
            eva_eve_evento_fk=evento,
            eva_eve_estado='Aprobado'
        ).first()

        if not inscripcion:
            messages.error(request, "❌ No tienes una inscripción activa para este evento.")
            return redirect('dashboard_evaluador')

        # Cambiar el estado a Cancelado
        inscripcion.eva_eve_estado = 'Cancelado'
        inscripcion.save()

        messages.success(request, f"✅ Has cancelado tu inscripción al evento '{evento.eve_nombre}'.")
        return redirect('dashboard_evaluador')
