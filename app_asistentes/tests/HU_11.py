""" Como Asistente Visualizar y Descargar la información detallada de la programación del evento en el que estoy inscrito para 
Tener mayor claridad sobre los horarios y los lugares en que se desarrollará cada actividad del evento 
"""

# app_asistentes/tests/HU_11.py

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from datetime import date
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection # Necesario para ejecutar SQL crudo

# Importaciones de modelos (Ajuste las rutas según su proyecto)
from app_usuarios.models import Usuario, Asistente, AdministradorEvento
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento


class AsistenteProgramacionTestCase(TestCase):
    """
    Casos de prueba para la Historia de Usuario (HU_11).
    Usa setUp(self) y tearDown(self) para garantizar el aislamiento y la limpieza de IDs.
    """
    
    def setUp(self): 
        """ 
        Configuración inicial: Crea todos los objetos necesarios ANTES de CADA TEST.
        """
        
        # --- AJUSTE DE UNICIDAD: Usuario Dummy (Consumirá ID 1) ---
        self.dummy_user = Usuario.objects.create_user(
            username='dummy_user_0', 
            email='dummy0@test.com', 
            password='password123', 
            rol=Usuario.Roles.VISITANTE
        )
        
        # --- Configuración de Usuarios y Roles ---
        
        # 1. Usuario para el Administrador de Evento (Consumirá ID 2)
        self.admin_user = Usuario.objects.create_user(
            username='admin_eve', 
            email='admin@test.com', 
            password='password123', 
            rol=Usuario.Roles.ADMIN_EVENTO
        )
        # ESTE es el punto de fallo recurrente (IntegrityError en usuario_id=2)
        self.administrador = AdministradorEvento.objects.create(
            usuario=self.admin_user, 
            cedula='100000000'
        )

        # 2. Usuario para Asistente Inscrito (Consumirá ID 3)
        self.asistente_inscrito_user = Usuario.objects.create_user(
            username='asi_inscrito', 
            email='asi_inscrito@test.com', 
            password='password123', 
            rol=Usuario.Roles.ASISTENTE
        )
        self.asistente_inscrito = Asistente.objects.create(
            usuario=self.asistente_inscrito_user, 
            cedula='111111111'
        )

        # 3. Usuario para Asistente NO Inscrito (Consumirá ID 4)
        self.asistente_no_inscrito_user = Usuario.objects.create_user(
            username='asi_no_inscrito', 
            email='asi_no_inscrito@test.com', 
            password='password123', 
            rol=Usuario.Roles.ASISTENTE
        )
        self.asistente_no_inscrito = Asistente.objects.create(
            usuario=self.asistente_no_inscrito_user, 
            cedula='222222222'
        )
        
        # --- Creación de Evento con archivos mock ---
        mock_image = SimpleUploadedFile("mock_image.png", b"file_content", content_type="image/png")
        mock_programacion_content = b"Contenido de la programacion detallada..."
        self.mock_programacion = SimpleUploadedFile("programacion.pdf", mock_programacion_content, content_type="application/pdf")

        self.evento = Evento.objects.create(
            eve_nombre='Conferencia de Testing',
            eve_descripcion='Detalles de la conferencia',
            eve_ciudad='Manizales',
            eve_lugar='Teatro',
            eve_fecha_inicio=date(2025, 12, 1),
            eve_fecha_fin=date(2025, 12, 3),
            eve_estado='Publicado', 
            eve_imagen=mock_image,
            eve_administrador_fk=self.administrador,
            eve_tienecosto='NO',
            eve_capacidad=200,
            eve_programacion=self.mock_programacion,
            preinscripcion_habilitada_asistentes=True
        )

        # --- Inscripción del Asistente ---
        mock_soporte = SimpleUploadedFile("soporte.pdf", b"soporte_content", content_type="application/pdf")
        AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente_inscrito,
            asi_eve_evento_fk=self.evento,
            asi_eve_fecha_hora='2025-10-10T10:00:00',
            asi_eve_estado='Aprobado', 
            asi_eve_soporte=mock_soporte,
            asi_eve_qr=mock_image,
            asi_eve_clave='CLAVE123'
        )

        self.detail_url = reverse('ver_info_evento_asi', kwargs={'pk': self.evento.pk})
        self.dashboard_url = reverse('dashboard_asistente')

    # --- MÉTODO PARA LIMPIEZA FORZADA DE AUTO_INCREMENT (SOLUCIÓN AL PROBLEMA DE MySQL) ---
    def tearDown(self):
        """ 
        Ejecuta comandos SQL crudos para resetear los contadores de ID.
        Esto es un hack necesario cuando MySQL no limpia AUTO_INCREMENT durante ROLLBACK.
        """
        table_names = [
            'app_usuarios_usuario', 
            'app_usuarios_administradorevento',
            'app_usuarios_asistente',
            'app_admin_eventos_evento',
            'app_asistentes_asistenteevento'
        ]
        
        with connection.cursor() as cursor:
            for table_name in table_names:
                # La sintaxis de MySQL/MariaDB para resetear AUTO_INCREMENT.
                # Establece el próximo ID disponible en 1.
                cursor.execute(f"ALTER TABLE {table_name} AUTO_INCREMENT = 1;")
    
    # --- Métodos de Ayuda ---
    def _login_as_asistente(self, asistente_user, asistente_obj):
        """ Método de ayuda para simular el inicio de sesión del Asistente. """
        client = Client()
        client.login(username=asistente_user.username, password='password123')
        session = client.session
        session['asistente_id'] = asistente_obj.pk
        session.save()
        return client

    # ----------------------------------------------------------------------
    # CP-HU1-001: Acceso Asistente Inscrito (Condición de Éxito)
    # ----------------------------------------------------------------------
    def test_cp_hu1_001_acceso_asistente_inscrito(self):
        """ Verifica que un Asistente inscrito acceda al detalle del Evento (HTTP 200) y vea la programación. """
        client = self._login_as_asistente(self.asistente_inscrito_user, self.asistente_inscrito) 
        
        response = client.get(self.detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'info_evento_evento_asi.html')
        self.assertContains(response, self.evento.eve_programacion.url)

    # ----------------------------------------------------------------------
    # CP-HU1-002: Restricción Asistente No Inscrito (Condición de Falla)
    # ----------------------------------------------------------------------
    def test_cp_hu1_002_restriccion_acceso_asistente_no_inscrito(self):
        """ Verifica que un Asistente NO inscrito sea redirigido y reciba un mensaje de error. """
        client = self._login_as_asistente(self.asistente_no_inscrito_user, self.asistente_no_inscrito)

        response = client.get(self.detail_url, follow=True) 

        self.assertRedirects(response, self.dashboard_url, status_code=302, target_status_code=200)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("No tienes permiso para ver este evento." in str(msg) for msg in messages))

    # ----------------------------------------------------------------------
    # CP-HU1-003: Descarga Programación (Verificación del Archivo)
    # ----------------------------------------------------------------------
    def test_cp_hu1_003_descarga_programacion_exitosa(self):
        """ Simula la solicitud directa al archivo de programación y verifica su contenido. """
        client = self._login_as_asistente(self.asistente_inscrito_user, self.asistente_inscrito)
        
        programacion_url = self.evento.eve_programacion.url
        
        download_response = client.get(programacion_url)
        
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response['Content-Type'], 'application/pdf')
        self.assertEqual(download_response.content, b"Contenido de la programacion detallada...")

    # ----------------------------------------------------------------------
    # CP-HU1-004: Evento Inexistente (Manejo de Error)
    # ----------------------------------------------------------------------
    def test_cp_hu1_004_acceso_evento_inexistente(self):
        """ Verifica HTTP 404 para un Evento inexistente (Event.pk no encontrado). """
        client = self._login_as_asistente(self.asistente_inscrito_user, self.asistente_inscrito)
        
        non_existent_pk = self.evento.pk + 999
        non_existent_url = reverse('ver_info_evento_asi', kwargs={'pk': non_existent_pk})

        response = client.get(non_existent_url)
        
        self.assertEqual(response.status_code, 404)