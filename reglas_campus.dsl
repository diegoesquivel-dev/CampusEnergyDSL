# CampusEnergyDSL - diez políticas del caso universitario.
# Las reglas describen propuestas; el prototipo solo simula decisiones.

# 1. Corte automático de climatización en aulas vacías.
REGLA ahorroBasico:
CUANDO codEspacio = "AULA302"
Y ocupacion = "VACIO"
Y tiempoVacio >= 15
Y actividadActual = "NINGUNA"
Y criticidad = "BAJA"
Y frescura = "ACTUALIZADO"
ENTONCES apagar(AULA302.AIRE02);

# 2. Reducción a modo ahorro en zonas comunes de tránsito.
REGLA ahorroPasillo:
CUANDO codEspacio = "PASILLOB1"
Y ocupacion = "VACIO"
Y tiempoVacio >= 20
Y (actividadActual = "NINGUNA" O criticidad = "BAJA")
Y frescura = "ACTUALIZADO"
ENTONCES modoAhorro(PASILLOB1.LUM01);

# 3. Recomendación de apagado en laboratorios.
REGLA revisionLaboratorio:
CUANDO codEspacio = "LABFISICA"
Y ocupacion = "VACIO"
Y tiempoVacio >= 30
Y actividadActual = "NINGUNA"
Y criticidad = "ALTA"
Y frescura = "ACTUALIZADO"
ENTONCES recomendarApagado(LABFISICA.EXTRACTOR01);

# 4. Alerta preventiva por telemetría degradada; nunca corta equipos.
REGLA alertaTelemetria:
CUANDO codEspacio = "LABQUIMICA"
Y (frescura = "OBSOLETO" O frescura = "DESCONECTADO")
ENTONCES emitirAlerta(LABQUIMICA.AIRE01);

# 5. Corte en hora punta por demanda neta elevada.
REGLA ahorroHoraPunta:
CUANDO codEspacio = "AULA302"
Y bloqueTarifa = "PUNTA"
Y demandaNeta > 10
Y ocupacion = "VACIO"
Y tiempoVacio >= 10
Y actividadActual = "NINGUNA"
Y frescura = "ACTUALIZADO"
ENTONCES apagar(AULA302.AIRE02);

# 6. Atenuación por baja generación solar y tarifa elevada.
REGLA atenuaSolarBaja:
CUANDO codEspacio = "PASILLOB1"
Y demandaNeta >= 8.5
Y (bloqueTarifa = "PUNTA" O bloqueTarifa = "MEDIA")
Y ocupacion = "VACIO"
Y frescura = "ACTUALIZADO"
ENTONCES modoAhorro(PASILLOB1.LUM01);

# 7. Alerta de excedente solar en horario valle.
REGLA excedenteSolarConfort:
CUANDO codEspacio = "AULA302"
Y demandaNeta <= 2
Y bloqueTarifa = "VALLE"
Y frescura = "ACTUALIZADO"
ENTONCES emitirAlerta(AULA302.AIRE02);

# 8. Respuesta a un evento externo de reducción del proveedor.
REGLA respuestaEventoProveedor:
CUANDO codEspacio = "PASILLOB1"
Y eventoProveedor = "REDUCCION"
Y demandaNeta > 5
Y criticidad != "EXTREMA"
Y frescura = "ACTUALIZADO"
ENTONCES apagar(PASILLOB1.LUM01);

# 9. Recomendación de reducción en laboratorio ante evento del proveedor.
REGLA reduccionLaboratorioEvento:
CUANDO codEspacio = "LABFISICA"
Y eventoProveedor = "REDUCCION"
Y bloqueTarifa = "PUNTA"
Y ocupacion = "VACIO"
Y actividadActual = "NINGUNA"
Y frescura = "ACTUALIZADO"
ENTONCES recomendarApagado(LABFISICA.EXTRACTOR01);

# 10. Alerta de protección del centro de datos ante evento del proveedor.
REGLA alertaCriticaProveedor:
CUANDO codEspacio = "DATACENTER01"
Y eventoProveedor = "REDUCCION"
Y criticidad = "EXTREMA"
ENTONCES emitirAlerta(DATACENTER01.SERVIDOR01);
