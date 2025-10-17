""" Como Asistente quiero Descargar el comprobante de inscripción a un evento (código QR) para 
Presentarlo y poder ingresar al evento"""




# app_asistentes.tests.HU_07.py

import tempfile
import os
from django.test import TransactionTestCase, Client # <-- IMPORTANTE: Cambiado a TransactionTestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from io import BytesIO 
from unittest.mock import patch, MagicMock
from django.core.management import call_command

# Importa los modelos necesarios
from app_usuarios.models import Asistente, AdministradorEvento
from app_admin_eventos.models import Evento
from app_asistentes.models import AsistenteEvento

# ----------------------------------------------------------------------
# FUNCIONES DE UTILIDAD (SIN CAMBIOS)
# ----------------------------------------------------------------------

Usuario = get_user_model() 

def crear_usuario_rol(username, rol, cedula, is_staff=False):
    """Crea un Usuario y su perfil asociado (Asistente o AdministradorEvento)."""
    # Siempre se crea primero el objeto base Usuario
    user = Usuario.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='testpassword123',
        rol=rol,
        cedula=cedula,
        is_staff=is_staff
    )
    
    # Luego se crea el perfil relacionado (OneToOneField)
    if rol == Usuario.Roles.ASISTENTE:
        return Asistente.objects.create(usuario=user)
    elif rol == Usuario.Roles.ADMIN_EVENTO:
        # Aquí es donde ocurría el error de clave duplicada
        return AdministradorEvento.objects.create(usuario=user) 
    
    return user

def crear_evento(admin_perfil, estado="Publicado", nombre="Evento Test", tienecosto="No"):
    """Crea un Evento con valores por defecto."""
    fecha_inicio = date.today() + timedelta(days=30)
    imagen_dummy = SimpleUploadedFile("logo.png", b"file_content", content_type="image/png")
    programacion_dummy = SimpleUploadedFile("prog.pdf", b"file_content", content_type="application/pdf")
    return Evento.objects.create(
        eve_nombre=nombre,
        eve_descripcion="Descripción del Evento",
        eve_ciudad="Ciudad Test",
        eve_lugar="Lugar Test",
        eve_fecha_inicio=fecha_inicio,
        eve_fecha_fin=fecha_inicio + timedelta(days=2),
        eve_estado=estado,
        eve_imagen=imagen_dummy,
        eve_administrador_fk=admin_perfil,
        eve_tienecosto=tienecosto,
        eve_capacidad=100,
        eve_programacion=programacion_dummy,
        preinscripcion_habilitada_asistentes=True
    )

def crear_inscripcion_asistente(asistente_perfil, evento, estado="Aprobado"):
    """Crea una inscripción de AsistenteEvento con un QR de prueba."""
    qr_content = b'Contenido del QR'
    qr_dummy = SimpleUploadedFile("qr_code.png", qr_content, content_type="image/png")
    soporte_dummy = SimpleUploadedFile("soporte.pdf", b"soporte_content", content_type="application/pdf")
    
    return AsistenteEvento.objects.create(
        asi_eve_asistente_fk=asistente_perfil,
        asi_eve_evento_fk=evento,
        asi_eve_fecha_hora=timezone.now(),
        asi_eve_estado=estado,
        asi_eve_soporte=soporte_dummy,
        asi_eve_qr=qr_dummy,
        asi_eve_clave="CLAVE123"
    )

# ----------------------------------------------------------------------
# CASOS DE PRUEBA: Descarga de Comprobante QR (HU_07)
# ----------------------------------------------------------------------

# Mockeamos el guardado de archivos para que los tests no escriban en disco.
@patch('django.core.files.storage.FileSystemStorage.save', MagicMock(return_value='dummy_path.png'))
@patch('django.db.models.fields.files.FieldFile.open', MagicMock(return_value=BytesIO(b'dummy content')))
class ComprobanteQRTestCase(TransactionTestCase): # <--- CLAVE: TransactionTestCase
    
    def setUp(self):
        """
        Setup que se ejecuta ANTES de CADA test.
        TransactionTestCase garantiza la limpieza y el reinicio de AUTO_INCREMENT
        necesario para bases de datos como MySQL/MariaDB.
        """
        
        self.client = Client()

        # 1. Crear perfiles de usuario 
        # Los IDs primarios se reiniciarán en cada test gracias a TransactionTestCase.
        admin_perfil = crear_usuario_rol('admin_test', Usuario.Roles.ADMIN_EVENTO, '1000', is_staff=True)
        self.asistente_aprobado = crear_usuario_rol('asistente_aprobado', Usuario.Roles.ASISTENTE, '1001')
        self.asistente_pendiente = crear_usuario_rol('asistente_pendiente', Usuario.Roles.ASISTENTE, '1002')
        self.asistente_rechazado = crear_usuario_rol('asistente_rechazado', Usuario.Roles.ASISTENTE, '1003')
        
        # 2. Crear los eventos
        self.evento_aprobado = crear_evento(admin_perfil, nombre="Evento para Aprobado")
        self.evento_pendiente = crear_evento(admin_perfil, nombre="Evento para Pendiente")
        self.evento_rechazado = crear_evento(admin_perfil, nombre="Evento para Rechazado")
        
        # 3. Crear las inscripciones con sus respectivos estados
        self.inscripcion_aprobada = crear_inscripcion_asistente(
            self.asistente_aprobado, self.evento_aprobado, estado="Aprobado"
        )
        self.inscripcion_pendiente = crear_inscripcion_asistente(
            self.asistente_pendiente, self.evento_pendiente, estado="Pendiente"
        )
        self.inscripcion_rechazada = crear_inscripcion_asistente(
            self.asistente_rechazado, self.evento_rechazado, estado="Rechazado"
        )
        
        # 4. Definir las URLs
        self.url_descarga_aprobado = reverse('ingreso_evento_asi', kwargs={'pk': self.evento_aprobado.pk})
        self.url_descarga_pendiente = reverse('ingreso_evento_asi', kwargs={'pk': self.evento_pendiente.pk})
        self.url_descarga_rechazado = reverse('ingreso_evento_asi', kwargs={'pk': self.evento_rechazado.pk})
        self.url_login = reverse('login_view') 

    # CP-AS-QR-001: Descarga exitosa del QR para una inscripción Aprobada. 
    def test_cp_as_qr_001_descarga_qr_aprobado(self):
        """Verifica que un Asistente Aprobado pueda acceder y ver el QR de ingreso."""
        self.client.login(username=self.asistente_aprobado.usuario.username, password='testpassword123')
        self.client.session['asistente_id'] = self.asistente_aprobado.pk
        self.client.session.save()
        
        response = self.client.get(self.url_descarga_aprobado)
        
        self.assertEqual(response.status_code, 200) 
        # Verifica que la URL del QR exista en el HTML renderizado
        self.assertContains(response, self.inscripcion_aprobada.asi_eve_qr.url) 
        self.assertContains(response, "Aprobado")
        
    # CP-AS-QR-002: Restricción de acceso al QR si la inscripción está en estado Pendiente.
    def test_cp_as_qr_002_restriccion_qr_pendiente(self):
        """Verifica que un Asistente Pendiente no tenga el QR visible, solo el estado."""
        self.client.login(username=self.asistente_pendiente.usuario.username, password='testpassword123')
        self.client.session['asistente_id'] = self.asistente_pendiente.pk
        self.client.session.save()
        
        response = self.client.get(self.url_descarga_pendiente)
        
        self.assertEqual(response.status_code, 200) 
        # Verifica que la URL del QR NO esté en el HTML
        self.assertNotContains(response, self.inscripcion_pendiente.asi_eve_qr.url)
        self.assertContains(response, "Pendiente") 

    # CP-AS-QR-004: Restricción de acceso al QR si la inscripción está Rechazada.
    def test_cp_as_qr_004_restriccion_qr_rechazado(self):
        """Verifica que un Asistente Rechazado no tenga el QR visible, solo el estado."""
        self.client.login(username=self.asistente_rechazado.usuario.username, password='testpassword123')
        self.client.session['asistente_id'] = self.asistente_rechazado.pk
        self.client.session.save()
        
        response = self.client.get(self.url_descarga_rechazado)
        
        self.assertEqual(response.status_code, 200) 
        self.assertNotContains(response, self.inscripcion_rechazada.asi_eve_qr.url)
        self.assertContains(response, "Rechazado")
        
    # CP-AS-QR-003: Requisito de Autenticación.
    def test_cp_as_qr_003_restriccion_no_autenticado(self):
        """Verifica que un usuario no autenticado sea redirigido al login."""
        self.client.logout()
        response = self.client.get(self.url_descarga_aprobado)
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(self.url_login))