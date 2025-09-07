from django.urls import path
from . import views



urlpatterns = [
    path('preins/asistente/<int:pk>', views.AsistenteCreateView.as_view(), name='crear_asistente'),

    path('dashboard/asistente', views.DashboardAsistenteView.as_view(), name='dashboard_asistente'),

    path('cambiar_password/asistente/', views.CambioPasswordAsistenteView.as_view(), name='cambio_password_asistente'),
    
    path('editar_preinscripcion_asistente/<int:asi_id>/', views.EditarPreinscripcionAsistenteView.as_view(),name='editar_preinscripcion_asistente'), 

    path('ver_detalle_evento/<int:pk>', views.EventoDetailView.as_view(), name='ver_info_evento_asi'),

    path('ingreso_evento_asistente/<int:pk>/', views.IngresoEventoAsistenteView.as_view(), name='ingreso_evento_asi'),

    path('asistente/eliminar/<int:asistente_id>/', views.EliminarAsistenteView.as_view(), name='eliminar_asistente'),

    path('evento/<int:evento_id>/memorias/asistente/', views.MemoriasAsistenteView.as_view(),name='memorias_asistente'),



    
]
    




