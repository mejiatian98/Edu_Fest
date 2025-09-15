
from django.urls import path, include
from app_admin_eventos import viewsorgin
from app_admin_eventos.viewsorgin import CertificadosView, cargar_personas

urlpatterns = [
    path('dashboard/admin/', viewsorgin.MenuPrincipalView.as_view(), name='dashboard_admin'),
    path('crear/', viewsorgin.EventoCreateView.as_view(), name='crear_evento'),
    path('crear_categoria_area/', viewsorgin.CreateCategoriaView.as_view(), name='crear_categoria_area'),
    path("lista_categorias/", viewsorgin.ListaCategoriasView.as_view(), name="lista_categorias"),
    path("eliminar_categoria/<int:pk>/", viewsorgin.eliminar_categoria, name="eliminar_categoria"),

    #Contraseña editar al iniciar la primera sesion
    path('cambiar_password/admin/', viewsorgin.CambioPasswordAdminView.as_view(), name='cambio_password_admin'),


    path('evento/editar/<int:pk>/', viewsorgin.EventoUpdateView.as_view(), name='editar_evento'),
    path('ver_info_evento/<int:pk>/', viewsorgin.EventoDetailView.as_view(), name='ver_info_evento_admin'),

    
    path('evento/<int:evento_id>/cancelacion/', viewsorgin.PageCancelarEventoView.as_view(), name='cancelar_evento_page'),
    path('evento/<int:pk>/cancelar_conteo/', viewsorgin.CancelarEventoView.as_view(), name='evento_estado_cancelado'),
    path('evento/<int:pk>/cancelar/', viewsorgin.EliminarDefiniEvento.as_view(), name='cancelar_evento'),

    path('evento/<int:evento_id>/revertir/', viewsorgin.RevertirCancelacionEventoView.as_view(), name='normal_evento'),
    path('evento/<int:evento_id>/cambiar_preinscripcion_asistente/', viewsorgin.CambiarPreinscripcionAsistenteView.as_view(), name='cambiar_preinscripcion_asistente'),
    path('evento/<int:evento_id>/cambiar_preinscripcion_participante/', viewsorgin.CambiarPreinscripcionParticipanteView.as_view(), name='cambiar_preinscripcion_participante'),
    path('evento/<int:evento_id>/cambiar_preinscripcion_evaluador/', viewsorgin.CambiarPreinscripcionEvaluadorView.as_view(), name='cambiar_preinscripcion_evaluador'),
    path('validaciones/<int:evento_id>/', viewsorgin.ValidacionesView.as_view(), name='validaciones'),
    
    path('validacion_asi/<int:evento_id>/', viewsorgin.ValidacionAsistentesView.as_view(), name='validacion_asi'),
    path('aprobar_asi/<int:evento_id>/<int:asistente_id>/', viewsorgin.AprobarAsistenteView.as_view(), name='aprobar_asi'),
    path('rechazar_asi/<int:evento_id>/<int:asistente_id>/', viewsorgin.RechazarAsistenteView.as_view(), name='rechazar_asi'),

    path('validacion_par/<int:evento_id>/', viewsorgin.ValidacionParticipanteView.as_view(), name='validacion_par'),
    path('aprobar_par/<int:evento_id>/<int:participante_id>/', viewsorgin.AprobarParticipanteView.as_view(), name='aprobar_par'),
    path('rechazar_par/<int:evento_id>/<int:participante_id>/', viewsorgin.RechazarParticipanteView.as_view(), name='rechazar_par'),

    path('estadisticas/<int:evento_id>/', viewsorgin.EstadisticasView.as_view(), name='estadisticas_evento'),


    path('ver_criterios/<int:evento_id>/', viewsorgin.CriterioListView.as_view(), name='ver_criterios'),
    path('ver_criterios_agregados/<int:evento_id>/', viewsorgin.CriterioAgregadosListView.as_view(), name='ver_criterios_agregados'),
    path('crear-criterio/<int:evento_id>/', viewsorgin.CrearCriterioView.as_view(), name='crear_criterio'),
    path('actualizar-criterio/<int:criterio_id>/', viewsorgin.ActualizarCriterioView.as_view(), name='actualizar_criterio'),
    path('eliminar-criterio/<int:criterio_id>/', viewsorgin.EliminarCriterioView.as_view(), name='eliminar_criterio'),

    path('ver_podio_admin/<int:evento_id>/', viewsorgin.VerPodioParticipantesAdminView.as_view(), name='ver_calificaciones_admin'),
    path('evento_admin/<int:evento_id>/participante/<int:participante_id>/detalle/',viewsorgin.DetalleCalificacionAdminView.as_view(),name='ver_detalle_calificacion_admin'),

    path('evento/<int:evento_id>/validacion_eva/', viewsorgin.ValidacionEvaluadorView.as_view(), name='validacion_eva'),
    path('evento/<int:evento_id>/aprobar_eva/<int:evaluador_id>/', viewsorgin.AprobarEvaluadorView.as_view(), name='aprobar_eva'),
    path('evento/<int:evento_id>/rechazar_eva/<int:evaluador_id>/', viewsorgin.RechazarEvaluadorView.as_view(), name='rechazar_eva'),

    path('administrador/editar/<int:administrador_id>/', viewsorgin.EditarAdministradorView.as_view(), name='editar_administrador'),

    path('evento/<int:pk>/info_tecnica/', viewsorgin.InformacionTecnicaEventoView.as_view(), name='ver_info_tecnica'),


    

    path('evento/<int:evento_id>/certificados/',CertificadosView.as_view(),name='certificados_admin'),

    # AJAX para cargar personas (sin @admin_required, usa login y session cookies)
    path('evento/cargar_personas/',cargar_personas,name='cargar_personas'),


    path('evento/<int:evento_id>/premiacion/',viewsorgin.PremiacionView.as_view(),name='premiacion_admin'),

    path('evento/<int:evento_id>/memorias/admin/',viewsorgin.MemoriasAdminView.as_view(),name='memorias_admin'),
    path('evento/<int:evento_id>/memoria/<int:memoria_id>/borrar/', viewsorgin.BorrarMemoriaAdminView.as_view(), name='borrar_memoria_admin'),




    path(
    "eventos/<int:evento_id>/previsualizar/<str:tipo>/<int:persona_id>/",
    viewsorgin.previsualizar_certificado,
    name="previsualizar_certificado"
),




    
    




]


