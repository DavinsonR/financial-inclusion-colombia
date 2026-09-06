-- 04_authorized_views.sql — publicar los marts sin dar acceso a las tablas crudas.
-- Una vista autorizada consulta tablas a las que quien la usa NO tiene permiso: el permiso lo tiene la vista.
-- Es el patrón que permite compartir resultados con un tablero o con un colaborador sin exponer la fuente.

CREATE SCHEMA IF NOT EXISTS `publico`
  OPTIONS (location = 'us-central1', description = 'Vistas autorizadas para consumo externo (tableros, colaboradores)');

CREATE OR REPLACE VIEW `publico.panel_departamento_anual` AS
SELECT * FROM `marts.mart_panel_departamento_anual`;

CREATE OR REPLACE VIEW `publico.panel_municipio_anual` AS
SELECT * FROM `marts.mart_panel_municipio_anual`;

-- Autorizar las vistas sobre el dataset de marts (sustituir <TU_PROYECTO>):
--   bq update --source /tmp/marts_access.json <TU_PROYECTO>:marts
-- donde el JSON incluye, dentro de "access":
--   {"view": {"projectId": "<TU_PROYECTO>", "datasetId": "publico", "tableId": "panel_departamento_anual"}}
--
-- Y dar a quien consume solo el rol roles/bigquery.dataViewer sobre el dataset `publico`:
--   bq add-iam-policy-binding --member="user:alguien@ejemplo.com" \
--      --role="roles/bigquery.dataViewer" <TU_PROYECTO>:publico
