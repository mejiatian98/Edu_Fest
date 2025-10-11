""" Como Asistente quiero Cancelar mi inscripción a un evento para 
Liberar mi cupo y que pueda ser utilizado por otra persona
"""

from datetime import date, timedelta
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

# 🚨 AJUSTA ESTAS IMPORTACIONES SI ES NECESARIO 🚨
from app_asistentes.models import AsistenteEvento
from app_usuarios.models import Asistente, AdministradorEvento 
from app_admin_eventos.models import Evento 


class CancelacionEventoAsistenteTests(TestCase):
    
    def setUp(self):
        # 1. Configuración de Usuario Asistente
        self.user_asistente = get_user_model().objects.create_user(
            username='testasi', email='asi@test.com', password='password'
        )
        self.asistente = Asistente.objects.create(usuario=self.user_asistente)
        
        # 2. Configuración de Usuario Administrador (Para crear Eventos)
        self.user_admin = get_user_model().objects.create_user(
            username='testadmin', email='admin@test.com', password='password_admin'
        )
        self.administrador = AdministradorEvento.objects.create(usuario=self.user_admin) 

        # 3. Evento Activo (Futuro)
        # 🔑 FIX 1: Añadir un valor a eve_imagen para evitar el ValueError en la plantilla
        self.evento_activo = Evento.objects.create(
            eve_nombre="Conferencia Futura",
            eve_fecha_inicio=date.today() + timedelta(days=5),
            eve_fecha_fin=date.today() + timedelta(days=10),
            eve_capacidad=100,
            eve_administrador_fk=self.administrador,
            eve_imagen='test_images/activo.jpg' 
        )

        # 4. Evento Finalizado (Pasado)
        # 🔑 FIX 1: Añadir un valor a eve_imagen para evitar el ValueError en la plantilla
        self.evento_finalizado = Evento.objects.create(
            eve_nombre="Evento Pasado",
            eve_fecha_inicio=date.today() - timedelta(days=10),
            eve_fecha_fin=date.today() - timedelta(days=5),
            eve_capacidad=50,
            eve_administrador_fk=self.administrador,
            eve_imagen='test_images/finalizado.jpg'
        )

        # 5. Inscripción APROBADA al evento activo
        self.inscripcion_activa = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente,
            asi_eve_evento_fk=self.evento_activo,
            asi_eve_estado='Aprobado',
            asi_eve_fecha_hora=timezone.now()
        )
        
        # 6. URLs
        self.url_cancelar_activo = reverse('cancelar_inscripcion_asistente', 
                                          kwargs={'evento_id': self.evento_activo.pk})
        self.url_cancelar_finalizado = reverse('cancelar_inscripcion_asistente', 
                                               kwargs={'evento_id': self.evento_finalizado.pk}) 
        
        # Usaremos el ID de un evento EXISTENTE (self.evento_activo) para el test 3,
        # pero modificaremos la inscripción DENTRO del test 3.
        self.url_cancelar_no_inscrito = self.url_cancelar_activo 
        self.url_dashboard = reverse('dashboard_asistente')


    # ----------------------------------------------------------------------
    # CASOS DE ÉXITO
    # ----------------------------------------------------------------------



    def test_cshr_002_prohibir_cancelacion_evento_finalizado(self):
        """CP-SHR-002: Verifica que no se puede cancelar un evento que ya finalizó (CA-10.1)."""
        
        # Creamos una inscripción Aprobada para el evento pasado
        inscripcion_finalizada = AsistenteEvento.objects.create(
            asi_eve_asistente_fk=self.asistente,
            asi_eve_evento_fk=self.evento_finalizado,
            asi_eve_estado='Aprobado',
            asi_eve_fecha_hora=timezone.now()
        )
        
        self.client.force_login(self.user_asistente)
        session = self.client.session
        session['asistente_id'] = self.asistente.id
        session.save()

        # Actuar: Intento de cancelar un evento finalizado
        response = self.client.post(self.url_cancelar_finalizado, follow=True)
        
        # 1. Assert: Redirección al dashboard
        self.assertRedirects(response, self.url_dashboard)

        # 2. Assert: Mensaje de error (CA-10.1)
        self.assertContains(response, "No puedes cancelar una inscripción a un evento que ya finalizó.", 
                            status_code=200)

        # 3. Assert: El estado de la inscripción sigue siendo 'Aprobado'
        inscripcion_finalizada.refresh_from_db()
        self.assertEqual(inscripcion_finalizada.asi_eve_estado, 'Aprobado')


    def test_cshr_003_no_inscripcion_activa(self):
        """CP-SHR-003: Verifica que si no hay inscripción activa, muestra error (CA-10.5)."""
        
        # 🔑 FIX 2: Eliminamos la inscripción ACTIVA creada en setUp para este evento.
        # Ahora el asistente NO tiene una inscripción en estado 'Aprobado' para el evento activo.
        self.inscripcion_activa.delete() 
        
        self.client.force_login(self.user_asistente)
        session = self.client.session
        session['asistente_id'] = self.asistente.id
        session.save()
        
        # Actuar: Intentamos cancelar el evento activo (donde ya no hay inscripción 'Aprobado')
        # Utilizamos self.url_cancelar_activo, que ahora es self.url_cancelar_no_inscrito
        response = self.client.post(self.url_cancelar_activo, follow=True)
        
        # 1. Assert: Redirección al dashboard (debe ser 302 -> 200)
        self.assertRedirects(response, self.url_dashboard)

        # 2. Assert: Mensaje de error (CA-10.5)
        self.assertContains(response, "No tienes una inscripción activa para este evento.", status_code=200)