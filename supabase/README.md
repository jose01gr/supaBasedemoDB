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