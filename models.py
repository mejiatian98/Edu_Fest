from decimal import Decimal
from django.db import models
from ckeditor.fields import RichTextField
from .utils_carrito import calcular_precio_final, calcular_subtotal, calcular_total_carrito
from cloudinary.models import CloudinaryField


    



# ========================
# CATEGORÍA Y PRODUCTOS
# ========================

class Categoria(models.Model):
    nombre_categoria = models.CharField(max_length=100, unique=True)
    descripcion = RichTextField(blank=True, null=True)

    def __str__(self):
        return self.nombre_categoria


class Subcategoria(models.Model):
    nombre_subcategoria = models.CharField(max_length=100)
    descripcion = RichTextField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')

    class Meta:
        unique_together = ('nombre_subcategoria', 'categoria')

    def __str__(self):
        return f'{self.nombre_subcategoria} ({self.categoria.nombre_categoria})'


class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion_corta = RichTextField(blank=True, null=True)
    descripcion = RichTextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.IntegerField(default=0, blank=True, null=True)
    cantidad = models.PositiveIntegerField()
    disponible = models.BooleanField(default=True, blank=True)
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.CASCADE, related_name='productos')
    es_destacado = models.BooleanField(default=False)
    es_destacado_principal = models.BooleanField(default=False)

    def __str__(self):
        return self.nombre

    def categoria(self):
        return self.subcategoria.categoria

    @property
    def imagen_principal(self):
        return self.imagenes.filter(es_principal=True).first()

    def save(self, *args, **kwargs):
        self.disponible = self.cantidad > 0
        super().save(*args, **kwargs)

    @property
    def precio_descuento(self):
        if self.descuento:
            return self.precio * (Decimal(1) - (Decimal(self.descuento) / Decimal(100)))
        return self.precio


class ProductoImagen(models.Model):
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, related_name='imagenes')
    imagen = CloudinaryField('imagen')
    es_principal = models.BooleanField(default=False)

    def __str__(self):
        return f"Imagen de {self.producto.nombre} {'(Principal)' if self.es_principal else ''}"


# ========================
# CLIENTE
# ========================

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    correo = models.EmailField(max_length=254)
    telefono = models.CharField(max_length=20)
    telefono_secundario = models.CharField(max_length=20, blank=True, null=True)
    ciudad = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.TextField()
    especificaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.nombre} {self.apellido or ""}'.strip()


# ========================
# CARRITO Y CARRITO ITEM
# ========================

class Carrito(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Carrito #{self.id}'

    def total(self):
        return calcular_total_carrito(self.items.all())


class CarritoItem(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'

    def precio_final(self):
        return calcular_precio_final(self.producto.precio, self.producto.descuento)

    @property
    def subtotal(self):
        return calcular_subtotal(self.precio_final(), self.cantidad)


# ============================= # 
# PEDIDO (se crea al confirmar) #
# ============================= #

class Pedido(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    carrito = models.OneToOneField(Carrito, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=[
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'), 
        ('rechazado', 'Rechazado'), 
        ('enviando', 'Enviando'), 
        ('entregado', 'Entregado'), 
        ('cancelado', 'Cancelado'),
    ])
    creado_en = models.DateTimeField(auto_now_add=True)

    stock_descontado = models.BooleanField(default=False)

    metodo_pago = models.CharField(max_length=20, choices=[
        ('nequi', 'Nequi'),
        ('contraentrega', 'Contraentrega'),
    ], default='contraentrega')

    def __str__(self):
        return f'Pedido #{self.id} - {self.cliente.nombre}'

    def total(self):
        return self.carrito.total()
