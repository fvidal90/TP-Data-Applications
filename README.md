# TP Data Apllications

En el presente repositorio se busca resolver un problema de Machine Learning completamente en AWS.

## Descripción del problema

Dado el siguiente [conjunto de datos](https://www.kaggle.com/datasets/yuanyuwendymu/airline-delay-and-cancellation-data-2009-2018),
Se busca, por año y aeropuerto, detectar días anómalos, en donde el concepto de anomalía viene dado por la demora 
promedio en la partida de los vuelos del día.

### Obtención de días anómalos

- Los modelos son por año y aeropuerto de origen.
- Solo se incluyen en el modelo los días cuya cantidad de vuelos sea mayor o igual a la mediana de la cantidad 
de vuelos por día con respecto al año y aeropuerto en cuestión.
- Para los días incluídos, se utiliza el siguiente modelo:
  - Feature: promedio de demora de la partida de los vuelos por día
  - Modelo: Isolation Forest
  - Parámetros:
    - random_state: 42
    - contamination: 0.05
- Los días cuya cantidad de vuelos sea menor a la mediana de la cantidad de vuelos por día con respecto al año.
- y aeropuerto en cuestión, no se consideran anómalos, con el fin de evitar distorsiones dadas por días con promedio de demora 
alto causado por un solo vuelo.

## Descripción de las partes de la arquitectura desarrollada.

### Región de AWS utilizada

`us-east-1`

### S3

Bucket llamado `flights-fer` con 2 keys principales:
- raw: contiene los csvs del dataset.
- reports: lugar donde se guardan los gráficos obtenidos. los mismos se guardan de la siguiente manera: 
`flights-fer/reports/{year}/{airport}/fig-{airport}-{year}.png`

Ejemplos de reportes se encuentran en la carpeta `s3_reports_examples`

Cifrado: SSE-S3.

### VPC

Red de Amazon en la región `us-east-1` con las siguientes configuraciones:
- 2 AZs: `us-east-1a` y `us-east-1b`.
- 3 subredes por AZ: 1 pública y 2 privadas.
  - Subred pública: para EC2.
  - Subredes privadas: para RDS y para la ENI que conecte a la RDS con Quicksight.

### RDS

Base de datos en Postgres para almacenar:
- Métricas:
  - Número de vuelos por día y aeropuerto.
  - Promedio de demora en los vuelos por día y aeropuerto.
- Anomalías:
  - Valor booleano por día y aeropuerto indicando si para ese aeropuerto el día en cuestión fue anómalo.

Cifrado: AWS-KMS (default). Especificación de la clave: SYMMETRIC_DEFAULT.

### Secrets manager

Valores secretos usados por la instancia de EC2 para:

- Levantar el repositorio (y en el branch en cuestión) en la instancia de EC2.
- Obtener los valores relevantes para conectarse a la base de datos de RDS.

Cifrado: AWS-KMS (default). Especificación de la clave: SYMMETRIC_DEFAULT.

### EC2

Servicio donde se corre airflow.
- Comentario: en esta primera versión, se corre en un docker-compose. 
Para una próxima versión, el siguiente paso sería deployar airflow en diferentes instancias de EC2 y 
una base de datos en RDS, con el fin de asegurar mayor disponibilidad, ante caída de alguna AZ.

### Quicksight

Servicio en donde se desarrolla una visualización de los datos cargados. Se conecta con RDS mediante una 
Elastic Network Interface (ENI).

Se crean dos paneles:
- Uno que muestra la cantidad de vuelos mensuales por aeropuerto.
- Uno que muestra la cantidad de días anómalos en cada trimestre (también por aeropuerto).

En la carpeta `quicksight_examples` hay un ejemplo de cada uno.

## Estructura del DAG de Airflow

- DAG: `tp_rds_solution`
- Tasks:
  - get_delay_task:
    - Lee el csv correspondiente al año en cuestión.
    - Calcula cantidad de vuelos y demora promedio por fecha y aeropuerto de salida.
    - Guarda las métricas diarias, por aeropuerto de salida, 
en la tabla `delay_metrics` de la base de datos.
  - get_anomalies_task:
    - Obtiene de la tabla `delay_metrics` las métricas diarias por aeropuerto de salida, 
correspondientes al año en cuestión.
    - Obtiene los días anómalos, para cada aeropuerto, en el año en cuestión.
    - Guarda los resultados en la tabla `delay_anomalies` de la base de datos, indicando para cada
(fecha, aeropuerto), si el día en cuestión fue anómalo o no en el respectivo aeropuerto.
  - report_anomalies_task:
    - Obtiene de las tablas `delay_metrics` y `delay_anomalies` las métricas diarias por aeropuerto 
del año en cuestión y, para cada (día, aeropuerto), si ese día fue anómalo o no 
en el aeropuerto en cuestión.
    - Genera, por cada aeropuerto, un gráfico con la cantidad de vuelos por días, 
indicando, para el respectivo aeropuerto, los días anómalos.
    - Guarda los gráficos en S3 en el bucket `flights-fer`, en la key `reports`.

## Instrucciones para crear y configurar los recursos necesarios para reproducir el desarrollo y dejarlo operativo.

Comentarios:
- Todo lo que se hace dentro de la consola, viene hecho con la cuenta de usuario en AWS Academy Learner Labs.
- En lo que hay que completar en consola, los nombres y contraseñas que se omitan pueden quedar a gusto del desarrollador.

### Creación de bucket en s3 y carga de los csvs.

Supuestos:
- El conjunto de datos ya fue descargado al local y los csvs se sitúan en el actual directorio dentro de 
la carpeta `files`
- El usuario ya tiene instalado `AWS Command Line Interface (AWS CLI)` y las configuraciones 
correspondientes para acceder a la cuenta de aws.

Pasos:
- Creación del bucket:
```aws s3api create-bucket --bucket flights-fer --region us-east-1```
- Encriptado del bucket con SSE-S3:
```
aws s3api put-bucket-encryption --bucket flights-fer --server-side-encryption-configuration '{
    "Rules": [
        {
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }
    ]
}'
```
- Bloqueo de acceso público:
```
aws s3api put-public-access-block \
    --bucket flights-fer \
    --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```
- Carga de los csvs:
```aws s3 sync ./files/ s3://flights-fer/raw/```

### Creación de la red VPC

- Creación de la red en la consola:
  - Dentro de VPC, `Crear VPC`
  - Configuraciones:
    - Recursos a crear: `VPC, subredes, etc.`
    - Bloque de CIDR IPv4: `10.0.0.0/16`
    - Sin Bloque de CIDR IPv6
    - Tenencia: Predeterminado
    - Zonas de disponibilidad: 2
    - Cantidad de subredes públicas: 2
    - Cantidad de subredes privadas: 4
    - Gateway NAT: Ninguna
    - Puntos de enlace de la VPC: Ninguna
- Renombre de subredes y tablas de ruteo
  - Dentro de subredes, renombrar las mismas para que tengan nombres más amigables:
    - tp-vidal-subnet-public-ec2-us-east-1a
    - tp-vidal-subnet-private-rds-us-east-1a
    - tp-vidal-subnet-private-quicksight-us-east-1a
    - tp-vidal-subnet-public-ec2-us-east-1b
    - tp-vidal-subnet-private-rds-us-east-1b
    - tp-vidal-subnet-private-quicksight-us-east-1b
  - Dentro de tablas de ruteo, nuevamente renombrar las mismas (y que tengan la asociación correcta con las subredes):
    - tp-vidal-rtb-public-ec2-us-east-1a
    - tp-vidal-rtb-private-rds-us-east-1a
    - tp-vidal-rtb-private-quicksight-us-east-1a
    - tp-vidal-rtb-public-ec2-us-east-1b
    - tp-vidal-rtb-private-rds-us-east-1b
    - tp-vidal-rtb-private-quicksight-us-east-1b
- Creación de grupos de seguridad
  - Tres grupos de seguridad:
    - ec2-sg
    - rds-sg
    - quicksight-sg
- reglas para los grupos de seguridad
  - ec2-sg:
    - Reglas de entrada:
      - TCP Personalizado, Puerto 8080, Origen: 0.0.0.0/0
      - SSH, Puerto 22, Origen: 0.0.0.0/0
    - Regla de salida:
      - Todo el tráfico, Destino: 0.0.0.0/0 (para poder guardar los gráficos en S3. Para poder pegarle a RDS, 
se puede hacer una más específica)
  - rds-sg:
    - Reglas de entrada:
      - PostgreSQL, origen `ec2-sg`
      - PostgreSQL, origen `quicksight-sg`
    - Regla de salida:
      - Todos los TCP, destino `quicksight-sg`
  - quicksight-sg:
    - Regla de entrada:
      - Todos los TCP, origen `rds-sg`
    - Regla de salida:
      - PostgreSQL, destino `rds-sg`
      
### Creación de base de datos postgres en RDS

- Creación de grupo de subredes:
  - En RDS - grupo de subredes, `crear grupo de subredes de base de datos`
  - Elegir la VPC creada anteriormente.
  - Seleccionar las zonas de disponibilidad `us-east-1a` y `us-east-1b`
  - Seleccionar las subredes correspondientes a RDS (cuidado: están por ID, no por nombre. 
Tener abierta otra ventana donde están los nombres y sus respectivos ID)
- Creación de base de datos:
  - En RDS - Bases de datos, `Crear base de datos`
  - Configuración:
    - Creación estándar
    - Motor: PostgreSQL
    - Versión: PostgreSQL 13.4-R1
    - Plantilla: Desarrollo y pruebas
    - Disponibilidad y durabilidad: Instancia de base de datos Multi-AZ
    - Clase de instancia de base de datos:
      - Clases con ráfagas (incluye clases t)
      - db.t3.micro
    - Almacenamiento:
      - Tipo de almacenamiento: SSD de uso general (gp2)
      - Almacenamiento asignado: 20 GiB
      - Habilitar escalado automático de almacenamiento
        - Umbral de almacenamiento máximo: 1000 GiB
    - Conectividad:
      - VPC: VPC creada.
      - Grupo de subredes: grupo de subredes creado.
      - Acceso público: no.
      - Grupo de seguridad de VPC
        - Elegir existente
          - `rds-sg`
      - Configuración adicional:
        - Puerto: 5432.
    - Autenticación de bases de datos:
      - Autenticación con contraseña.
    - Configuración adicional:
      - Opciones de base de datos: 
        - Grupo de parámetros de base de datos: default.postgres13
      - Copia de seguridad
        - Habilitar las copias de seguridad automatizadas.
        - Periodo de retención de copia de seguridad: 1 día.
        - Periodo de copia de seguridad: Sin preferencia.
        - Copiar las etiquetas en las instantáneas
        - Replicación de copias de seguridad: NO Habilitar la replicación en otra región de AWS
      - Cifrado:
        - Habilitar el cifrado
        - Clave de AWS KMS: (default) aws/rds
      - Información sobre rendimiento: NO Habilitar información sobre rendimiento
      - Monitoreo: NO Habilitar la monitorización mejorada
      - Exportaciones de registros: NO seleccionar ninguno de los dos tipos.
      - Mantenimiento:
        - Habilitar actualización automática de versiones secundarias.
        - Período de mantenimiento: sin preferencia.
      - Protección contra eliminación: NO Habilitar la protección contra la eliminación (para poder crear y borrar sin problemas, 
al ser una etapa de prueba.).

### Creación de credenciales en Secrets Manager

- Credenciales de github:
  - Requisito:
    - Generación de token de acceso personal en github:
      - Dentro de github ir a settings - Developer settings - Personal access tokens
      - Generar un nuevo token:
        - Scopes: repo
  - Creación de credenciales:
    - En AWS Secrets Mmanager, `Almacenar un secreto nuevo`
    - Configuración:
      - Tipo de secreto: `Otro tipo de secreto`
      - claves-valor:
        - GITHUB_USER
        - GITHUB_EMAIL
        - GITHUB_TOKEN
        - GITHUB_BRANCH
      - Clave de cifrado: aws/secretsmanager
      - Nombre del secreto: `github_credentials`
      - Todo lo restante se puede saltear (No configurar rotación automática)
- Credenciales de postgres:
  - Creación de credenciales:
    - Configuración:
      - Tipo de secreto: `Credenciales para la base de datos de Amazon RDS`
      - Credenciales: usuario y contraseña definidos en la creación de la base de datos
      - Clave de cifrado: aws/secretsmanager
      - Base de datos: seleccionar la base de datos creada.
      - Nombre del secreto: `pg_credentials`
      - Todo lo restante se puede saltear (No configurar rotación automática)

### Creación de la instancia de EC2 y ejecución del DAG de Airflow

- Lanzamiento de instancias:
  - En EC2 - Instancias: `Lanzar Instancias`
  - Configuración:
    - Amazon Linux 2 AMI (HVM) - Kernel 5.10, SSD Volume Type - ami-0c02fb55956c7d316 (64 bits x86) / ami-03190fe20ef6b1419 (64 bits Arm)
      - 64 bits x86
    - Instance Type: t2.large
    - Configuración (cambios de lo que viene por default):
      - red: elegir la red creada
      - subred: elegir la subred pública creada para EC2 en us-east-1b.
      - Asignar automáticamente IP pública: Habilitar
      - Rol de IAM: `LabInstanceProfile` (para adjuntar el rol `LabRole` y tener permiso a diferentes servicios, como S3)
      - Detalles avanzados
        - Datos de usuario: subir el archivo config.sh de este repositorio.
    - Adición de almacenamiento: 16 GiB
    - Security group: seleccionar `ec2-sg`
    - Claves: continuar sin par de claves y conectarse desde la consola (prácticamente no hay necesidad de conectarse a la instancia).
- Ejecución del DAG:
  - Aguardar a que se lance la instancia y se inicie Airflow.
  - Entrar a http://{IPv4 pública}:8080/
  - Ingresar con usuario `airflow` y contraseña `airflow`
  - Activar el DAG `tp_rds_solution`.
  - Al ser un DAG que terminó en 2018, al completarse la ejecución se puede terminar la instancia.

### Visualización en Quicksight

- Creación de cuenta en AWS Quicksight
  - Dentro de la consola de AWS, entrar a `Quicksight`
  - Crear la cuenta, en la versión `Enterprice  edition` (para poder crear la conexión a la VPC)
- Crear conexión VPC
  - En la parte superior derecha, desplegar y seleccionar `Administrar QuickSight`
  - Ir a `Administrar conexiones VPC`
  - Seleccionar `Añadir conexión con VPC`
  - Elegir la VPC creada
  - Elegir la subred creada para Quicksight en us-east-1b
  - Elegir el grupo de seguridad cread para Quicksight
  - Comentario: en los últimos dos pasos, tanto la VPC como el grupo de seguridad se seleccionan 
por ID, por lo que se necesita tener en otra pestaña la sección VPC abierta.
- Crear los conjuntos de datos (repetir para cada tabla):
  - Ir a `Conjunto de datos` y seleccionar `Nuevo conjunto de datos`
  - Seleccionar `RDS`
  - Completar con el ID de la instancia de base de datos, la conexión creada anteriormente, y los datos
(Nombre de la base de datos, usuario y contraseña) asociados a la base de datos.
  - Ir a `Crear origen de datos`
  - Seleccionar la tabla en cuestión y apretar `Seleccionar`
  - Tildar `Importar a SPICE para un análisis más rápido` y seleccionar `Visualize`
- Crear análisis y publicar paneles:
  - En el punto anterior, se crearon dos análisis en blanco (`delay_metrics analysis` y `delay_anomalies analysis`)
  - En `delay_metrics analysis`:
    - Seleccionar `Gráfico de líneas`
    - Configurar:
      - Eje X: `fl_date`
        - Agregar: Mes
        - Formato: Formato Personalizado `YYYY/MM`
      - Valor: `number_of_flights (Suma)`
      - Color: `origin`
    - Crear parámetros:
      - En `Parámetros` apretar `+`
      - Crear los siguientes parámetros:
        - StartDate:
          - Tipo de datos: `fecha y tiempo`
          - Grado de detalle: `día`
          - Fecha predeterminada: `2009/01/01`
          - Apretar `definir valor predeterminado dinámico`, elegir las opciones que aparecen y `Aplicar`
          - Apretar `Crear` y `Cerrar`
        - EndDate:
          - Tipo de datos: `fecha y tiempo`
          - Grado de detalle: `día`
          - Fecha predeterminada: `2019/01/01`
          - Apretar `definir valor predeterminado dinámico`, elegir las opciones que aparecen y `Aplicar`
          - Apretar `Crear` y `Cerrar`
        - Origin:
          - Tipo de datos: `cadena`
          - Valores: `valores múltiples`
          - Dejar en blanco `Valores predeterminados múltiples estáticos`
          - No tildar `Mostrar como vacío de forma predeterminada`
          - Apretar `definir valor predeterminado dinámico`, elegir las opciones que aparecen y `Aplicar`
          - Apretar `Crear` y `Cerrar`
    - Añadir control a los parámetros
      - En cada uno de los parámetros, seleccionar Añadir control:
        - StartDate:
          - Nombre para mostrar: `start date`
          - Estilo: `selector de fechas`
          - Formato de fecha `YYYY/MM`
        - EndDate:
          - Nombre para mostrar: `end date`
          - Estilo: `selector de fechas`
          - Formato de fecha `YYYY/MM`
        - Origin:
          - Nombre para mostrar: `origin`
          - Estilo: `Menú desplegable: selección múltiple`
          - Valores: `Enlazar a un campo del conjunto de datos`
            - Elegir las opciones que aparecen
    - Agregar filtros
      - Ir a la sección `Filtro`
      - fl_date:
        - Usar parámetros
        - Entre `StartDate` y `EndDate`, incluyendo fecha de inicio y excluyendo fecha de finalización.
      - origin:
        - Tipo de filtro: `filtro personalizado`
        - Usar parámetros: `Origin`
    - Dentro de la visualización:
      - Ocultar: `Otro`
      - `Formato del elemento visual`
        - Editar título: `Number of flights per airport between ${StartDate} and ${EndDate}`
        - No mostrar subtítulo
        - Eje X - título: `Date`
        - Eje Y - título: `Number of flights`
    - Compartir panel:
      - Arriba a la derecha ir a `Compartir` - `Publicar panel`
  - En `delay_anomalies analysis`:
    - Seleccionar `Gráfico de líneas`
    - Configurar:
      - Eje X: `fl_date`
        - Agregar: Trimestre
        - Formato: Formato Personalizado `YYYY Q`
      - Valor: `anomaly (Suma)`
      - Color: `origin`
    - Crear parámetros:
      - Similar al caso anterior
    - Añadir control a los parámetros:
      - En cada uno de los parámetros, seleccionar Añadir control:
        - StartDate:
          - Nombre para mostrar: `start date`
          - Estilo: `selector de fechas`
          - Formato de fecha `YYYY Q`
        - EndDate:
          - Nombre para mostrar: `end date`
          - Estilo: `selector de fechas`
          - Formato de fecha `YYYY Q`
        - Origin:
          - Nombre para mostrar: `origin`
          - Estilo: `Menú desplegable: selección múltiple`
          - Valores: `Enlazar a un campo del conjunto de datos`
            - Elegir las opciones que aparecen
      - Agregar filtros
        - Similar al caso anterior
      - Dentro de la visualización:
        - Ocultar: `Otro`
        - `Formato del elemento visual`
          - Editar título: `Días anómalos por Q por aeropuerto entre ${StartDate} y ${EndDate}`
          - No mostrar subtítulo
          - Eje X - título: `Date`
          - Eje Y - título: `Anomaly days`
      - Compartir panel:
        - Arriba a la derecha ir a `Compartir` - `Publicar panel`
