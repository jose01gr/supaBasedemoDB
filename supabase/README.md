# Demo Sellercloud → Supabase

## Objetivo

Construir una primera demo para extraer clientes desde Sellercloud y cargarlos en una base de datos Supabase/PostgreSQL.

## Estado actual

La conexión con Sellercloud funciona correctamente usando el dominio API:

```env
SELLERCLOUD_BASE_URL=https://fc2.api.sellercloud.com

## Tabla locas en supabase:
sellercloud_customers

## Filtro usado para la demo:
model.channel=21

## Endpoint usado:
/rest/api/Customers?model.channel=21&model.pageNumber={page}&model.pageSize={PAGE_SIZE}

## Demo técnica: Sellercloud + Bigin + Supabase

Esta demo centraliza datos de clientes desde Sellercloud y contactos activos desde Bigin en una base de datos PostgreSQL local usando Supabase.

### Objetivo

Validar que la empresa puede tener una base de datos propia para comparar información entre plataformas externas, detectar coincidencias, diferencias y registros pendientes de revisión.

### Fuentes conectadas

- Sellercloud: clientes del canal `model.channel=21`
- Bigin: contactos con tag `V - Cliente Activo`
- Supabase/PostgreSQL local: almacenamiento y comparación

### Resultados actuales

- Sellercloud customers: 652
- Bigin active contacts: 591
- Email and name match: 335
- Email match, name different: 182
- Name match, email different: 44
- Pending review: 84

### Vistas principales

- `customer_bigin_comparison_v2`
- `customer_bigin_pending_review`
- `customer_bigin_demo_summary`

### Histórico

La tabla `customer_match_snapshots` guarda snapshots de comparación para medir cambios entre ejecuciones.

Script para generar snapshot:

```bash
python scripts/create_customer_match_snapshot.py