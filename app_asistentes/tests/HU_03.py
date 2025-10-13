""" Como visitante web quiero Acceder a 
información detallada sobre los eventos de mi interés para 
Tener mayor claridad sobre mi posibilidad e interés de asistir"""


# app_asistentes/tests/HU_03.py

from django.test import TestCase, Client
from django.urls import reverse
from app_admin_eventos.models import Evento 
# Asegúrate de que las importaciones son correctas
from app_usuarios.models import Usuario, AdministradorEvento 
from datetime import date
from unittest.mock import MagicMock

class VisitanteWebEventosTestCase(TestCase):
    """
    Casos de prueba para la funcionalidad de visualización de eventos por un Visitante Web.
    Se implementa la estrategia de "Salto de ID Extremo" para resolver el IntegrityError (1062) en MySQL.
    """
    
    @classmethod
    def setUpTestData(cls):
        # ⚠️ SOLUCIÓN ROBUSTA PARA MYSQL/IntegrityError (1062) ⚠️
        # Creamos 50 usuarios fantasma para garantizar que el ID autoincremental de nuestro
        # usuario real (cls.user_admin) sea > 50. Esto mitiga la colisión
        # causada por la retención de secuencias de auto-incremento en MySQL.
        for i in range(1, 51): # Crea 50 usuarios 'fantasma' (IDs 1 a 50)
            Usuario.objects.create_user(
                username=f'fantasma_user_{i}', 
                email=f'fantasma_{i}@temp.com', 
                password='dummy', 
                rol=Usuario.Roles.ASISTENTE, 
                # Aseguramos que la cédula sea única
                cedula=f'99999999{i:02d}X' 
            )
        
        # 1. Crear el Administrador de Evento para la prueba (Obtendrá ID 51 o superior)
        cls.user_admin = Usuario.objects.create_user(
            username='admin_test_eve_01_hu03', # Un nombre de usuario más específico
            email='admin_test_01_hu03@eventsoft.com', 
            password='password123', 
            rol=Usuario.Roles.ADMIN_EVENTO, 
            cedula='111111111B' # Cédula única y diferente de los fantasmas
        )
        
        # 1.b. Creación del perfil AdministradorEvento
        # El usuario_id que se insertará será un valor alto.
        cls.admin_evento = AdministradorEvento.objects.create(usuario=cls.user_admin)
        
        # 2. Crear Eventos en diferentes estados
        fecha_actual = date.today()
        
        cls.evento_publicado = Evento.objects.create(
            eve_nombre="Congreso de IA Publicado",
            eve_descripcion="Evento visible para el publico.",
            eve_estado="Publicado",
            eve_administrador_fk=cls.admin_evento,
            eve_ciudad="Bogota",
            eve_lugar="Centro de Convenciones",
            eve_fecha_inicio=fecha_actual,
            eve_fecha_fin=fecha_actual,
            eve_tienecosto='Sí',
            eve_capacidad=100,
            eve_imagen=MagicMock(name='FileField_img_pub'), 
            eve_programacion=MagicMock(name='FileField_prog_pub'),
        )
        cls.evento_cancelado = Evento.objects.create(
            eve_nombre="Taller de Python Cancelado",
            eve_descripcion="Evento cancelado, no debe ser visible.",
            eve_estado="Cancelado",
            eve_administrador_fk=cls.admin_evento,
            eve_ciudad="Medellin",
            eve_lugar="Universidad X",
            eve_fecha_inicio=fecha_actual,
            eve_fecha_fin=fecha_actual,
            eve_tienecosto='No',
            eve_capacidad=50,
            eve_imagen=MagicMock(name='FileField_img_can'),
            eve_programacion=MagicMock(name='FileField_prog_can'),
        )
        cls.evento_finalizado = Evento.objects.create(
            eve_nombre="Webinar de Django Finalizado",
            eve_descripcion="Evento finalizado, no debe ser visible.",
            eve_estado="Finalizado",
            eve_administrador_fk=cls.admin_evento,
            eve_ciudad="Cali",
            eve_lugar="Online",
            eve_fecha_inicio=date(2020, 1, 1), 
            eve_fecha_fin=date(2020, 1, 1),
            eve_tienecosto='No',
            eve_capacidad=200,
            eve_imagen=MagicMock(name='FileField_img_fin'),
            eve_programacion=MagicMock(name='FileField_prog_fin'),
        )
        
        cls.client = Client()

    # --- Casos de Prueba de Listado (Página Principal) ---
    
    def test_cp01_acceso_pagina_principal_visitante(self):
        """CA01: Verifica acceso a la página principal sin autenticación (HTTP 200)."""
        response = self.client.get(reverse('pagina_principal'))
        self.assertEqual(response.status_code, 200)
        
    def test_cp02_solo_muestra_eventos_publicados_en_listado(self):
        """CA02: Verifica que solo los eventos 'Publicado' aparecen en el listado."""
        response = self.client.get(reverse('pagina_principal'))
        eventos_en_contexto = response.context['object_list'] 
        
        self.assertEqual(len(eventos_en_contexto), 1)
        self.assertEqual(eventos_en_contexto[0].eve_nombre, self.evento_publicado.eve_nombre)

    # --- Casos de Prueba de Detalle de Evento ---
    
    def test_cp03_acceso_detalle_evento_publicado(self):
        """CA03, CA05: Verifica acceso exitoso y contenido de un evento 'Publicado'."""
        url = reverse('ver_info_evento', kwargs={'pk': self.evento_publicado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertIn('object', response.context)
        self.assertEqual(response.context['object'].pk, self.evento_publicado.pk)
        self.assertContains(response, "Congreso de IA Publicado")

    def test_cp04_no_acceso_detalle_evento_cancelado(self):
        """CA04: Verifica que NO se puede acceder al detalle de un evento 'Cancelado' (HTTP 404)."""
        url = reverse('ver_info_evento', kwargs={'pk': self.evento_cancelado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)

    def test_cp05_no_acceso_detalle_evento_finalizado(self):
        """CA04: Verifica que NO se puede acceder al detalle de un evento 'Finalizado' (HTTP 404)."""
        url = reverse('ver_info_evento', kwargs={'pk': self.evento_finalizado.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)











        