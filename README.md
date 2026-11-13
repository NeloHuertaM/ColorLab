# Color Match para DaVinci Resolve

Script para DaVinci Resolve que gradúa planos automáticamente a partir de una referencia:

- **Igualar planos**: colocas el cursor sobre el plano de referencia y el resto de planos de la pista se igualan a él en exposición, balance de blancos, contraste y paleta.
- **Transferir look**: eliges una imagen externa (un fotograma de una película, una foto, un still) y su look se transfiere a los planos.
- Cada corrección se genera como una **LUT 3D `.cube` de 33 puntos** y se aplica sola a un nodo de cada plano con la API de scripting (`Graph.SetLUT`), sin exportar ni importar nada a mano.
- Controles de **intensidad**, **protección de tonos de piel** y **protección de altas luces**.

El motor es estadístico (no es una red neuronal): mide la distribución de color de cada fotograma en el espacio perceptual Oklab y calcula la transformación que la lleva a la de la referencia. Es rápido (menos de un segundo por plano), determinista y no necesita GPU ni conexión.

## Compatibilidad: Resolve gratuito frente a Studio

Esto es lo más importante antes de instalar. Blackmagic ha ido limitando el scripting en la versión gratuita:

| Versión de Resolve | ¿Funciona el script? | Interfaz |
| --- | --- | --- |
| **Studio** (18.5 o superior, incluida 21.x) | Sí | Ventana nativa (UIManager) |
| Gratuita 18.x a 19.0.x | Sí | Ventana nativa (UIManager) |
| Gratuita 19.1 a 21.0.4 | Sí | Ventana alternativa (tkinter), porque UIManager está bloqueado en la gratuita desde 19.1 |
| Gratuita 21.1 o superior | **No**: desde 21.1 la gratuita ya no ejecuta scripts Python | Usa la línea de comandos (ver más abajo) y carga la LUT a mano |

Otros límites de la API que afectan al plugin:

- **Scripting externo** (lanzar scripts desde fuera de Resolve) es solo de Studio. Este plugin no lo necesita: se ejecuta desde el menú *Workspace > Scripts*, dentro de Resolve.
- **Workflow Integration plugins** (paneles HTML/Electron) son solo de Studio. Por eso el plugin usa un script normal en lugar de un panel.
- `Graph.SetLUT` solo acepta LUTs que Resolve ya conoce. El script escribe las LUTs dentro de la carpeta maestra de LUTs y llama a `Project.RefreshLUTList()` antes de aplicarlas.
- `TimelineItem.GetNodeGraph()` y `Graph.SetNodeEnabled()` son de versiones recientes. En versiones antiguas el script usa los métodos (ya obsoletos) `TimelineItem.SetLUT` / `GetNumNodes` y no puede desactivar el nodo antes de capturar (ver *Limitaciones*).
- La API no expone la selección de planos de la línea de tiempo. Para elegir qué planos graduar se usa la pista y, opcionalmente, el **color de clip** (marca los planos con un color en la página Edit).

Fuentes: documentación de la API de scripting v21.0.4 (copia en [gist de X-Raym](https://gist.github.com/X-Raym/2f2bf453fc481b9cca624d7ca0e19de8)), [foro de Blackmagic sobre UIManager en 19.1](https://forum.blackmagicdesign.com/viewtopic.php?t=213158), [Puget Systems sobre Resolve 21.1 gratuito](https://www.pugetsystems.com/blog/2026/09/10/how-davinci-resolve-free-v21-1-scripting-changes-affect-puget-bench/). Blackmagic no siempre documenta estos cambios en las notas de versión, así que conviene comprobarlo en tu versión.

## Requisitos

- DaVinci Resolve (ver tabla anterior).
- Python 3.8 o superior de **64 bits**, instalado para todos los usuarios. Resolve usa el Python del sistema.
- `numpy` instalado en ese Python. `Pillow` es opcional pero recomendable (lee TIFF y JPG, y decodifica PNG más rápido).

## Instalación

1. Copia esta carpeta a una ubicación fija, por ejemplo `C:\Proyectos\resolve-colormatch` (Windows) o `~/resolve-colormatch` (macOS/Linux). El script instalado apunta a ella, así que no la muevas después.
2. Instala las dependencias en el Python que usa Resolve:

   ```bash
   python -m pip install numpy pillow
   ```

3. Instala el script en el menú de Resolve:

   ```bash
   python install.py
   ```

   Copia `ColorMatch.py` a la carpeta de scripts de tu usuario:

   - Windows: `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility`
   - macOS: `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Utility`
   - Linux: `~/.local/share/DaVinciResolve/Fusion/Scripts/Utility`

   Con `--target <carpeta>` puedes elegir otra carpeta de scripts.

4. Comprueba que la carpeta de LUTs se puede escribir. Por defecto es una subcarpeta `ColorMatch` dentro de la carpeta maestra de LUTs:

   - Windows: `C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\LUT\ColorMatch`
   - macOS: `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/ColorMatch`
   - Linux: `/opt/resolve/LUT/ColorMatch`

   En macOS y Linux puede que necesites crearla una vez con permisos de administrador y dar permiso de escritura a tu usuario. Puedes abrir la carpeta maestra desde *Project Settings > Color Management > Open LUT Folder*.

5. Reinicia Resolve. El script aparece en **Workspace > Scripts > ColorMatch**.

Para desinstalar: `python install.py --uninstall`.

## Uso

### Preparar los planos

- Añade al final del árbol de nodos de cada plano un **nodo en serie vacío** dedicado a la igualación. Por defecto el script escribe en el **último nodo** (opción *Nodo = 0*).
- Si no quieres graduar todos los planos de la pista, márcalos con un color de clip (clic derecho > *Clip Color* en la página Edit) y elige ese color en el script.

### Igualar planos

1. Ve a la página **Color** y coloca el cursor en el fotograma del plano de referencia que mejor lo represente.
2. Abre *Workspace > Scripts > ColorMatch*.
3. Modo: *Igualar planos al plano bajo el cursor*. Elige la pista de vídeo, el filtro de color y el nodo.
4. Pulsa **Graduar planos**. Para cada plano el script mueve el cursor a su fotograma central, desactiva el nodo de igualación, captura el fotograma, calcula la LUT, la escribe en la carpeta de LUTs y, al final, la aplica al nodo. El cursor vuelve a donde estaba.

### Transferir un look

1. Modo: *Transferir el look de una imagen externa* y elige la imagen (PNG, TIFF o JPG).
2. Ajusta la intensidad y las protecciones y pulsa **Graduar planos**. En este modo se gradúan todos los planos de la pista (o los del color elegido).

### Parámetros

| Parámetro | Efecto |
| --- | --- |
| Método | *Lineal MKL*: transforma media y covarianza; estable, ideal para igualar planos. *Transporte óptimo por cortes*: además iguala la forma de la distribución (virados en sombras y luces); mejor para looks. *Reinhard*: media y desviación por canal; el más simple. |
| Intensidad | Mezcla entre la imagen original (0) y la corrección completa (100). Va horneada en la LUT; para cambiarla vuelve a ejecutar el script o baja el *Key Output Gain* del nodo. |
| Proteger tonos de piel | Los colores de piel conservan su tono y saturación originales y solo siguen el cambio de luminosidad. |
| Proteger altas luces | Las altas luces conservan su croma original (blancos sin teñir) y la luminosidad entra con un hombro suave en vez de recortar. |

Al cambiar de modo se cargan valores por defecto razonables: igualar planos usa MKL sin protección de piel y protección de altas luces baja; transferir look usa transporte óptimo con ambas protecciones al 50 %.

## Línea de comandos (sin Resolve)

Útil para Resolve gratuito 21.1 o posterior, para probar ajustes o para trabajar con otras aplicaciones que lean `.cube`:

```bash
python -m colormatch plano.png referencia.png correccion.cube --mode match --preview plano_corregido.png
```

```bash
python -m colormatch plano.png look.jpg look.cube --mode look --strength 0.8 --skin 0.6
```

Opciones: `--method {reinhard,mkl,sliced}`, `--strength`, `--skin`, `--highlights` (entre 0 y 1), `--size` (puntos de la LUT, 33 por defecto) y `--preview` para guardar el plano corregido. En modo *match*, si las dos imágenes tienen el mismo tamaño, muestra el Delta E 2000 medio antes y después.

En Resolve gratuito 21.1 exporta los fotogramas con *Grab Still* y *Export* en la galería, genera la LUT con este comando y cárgala en el nodo (clic derecho > *LUTs*) tras *Update Lists*.

## Cómo funciona

1. Cada fotograma se reduce a unos 512 píxeles de lado para medir estadísticas, se pasa de RGB de pantalla a lineal y de ahí a **Oklab**, un espacio perceptual donde las distancias se parecen a las diferencias que vemos. Se descartan los píxeles negros puros o recortados si son minoría.
2. Se ajusta una transformación de la distribución del plano a la de la referencia:
   - **MKL** (Monge-Kantorovich lineal): la transformación afín óptima entre dos gaussianas; corrige exposición, balance de blancos, contraste y saturación a la vez.
   - **Transporte óptimo por cortes**: tras MKL, 10 iteraciones de igualación de histogramas sobre rotaciones aleatorias 3D (semilla fija, resultado determinista).
   - **Reinhard**: media y desviación típica por canal.

   Las ganancias están acotadas para que un fotograma plano o monocromo no dispare valores extremos.
3. Se aplican las protecciones de piel y altas luces, y la intensidad.
4. La transformación se evalúa sobre una retícula de 33 × 33 × 33 colores y se escribe como `.cube` (rojo varía más rápido, dominio 0 a 1).

## Limitaciones conocidas

- **Una muestra por plano**: se analiza el fotograma central de cada plano. Planos con cambios fuertes de luz pueden necesitar retoques.
- **Espacio de color**: las capturas son la salida del visor (espacio de salida de la línea de tiempo) y la LUT se construye en ese espacio. Funciona de forma exacta en proyectos *DaVinci YRGB* sin gestión de color o cuando el espacio de la línea de tiempo coincide con el de salida (por ejemplo Rec.709). Con *Color Managed* o ACES, la LUT trabaja sobre los valores del nodo y el resultado puede desviarse; en ese caso baja la intensidad o usa la línea de comandos sobre capturas en el espacio de la línea de tiempo.
- **Nodo de igualación al final**: si hay nodos después del nodo de la LUT, transformarán la corrección y la igualación no será exacta.
- **Versiones sin `SetNodeEnabled`**: si vuelves a ejecutar el script sobre los mismos planos, la captura incluye la LUT anterior y la nueva se acumula encima. Resetea el nodo antes de repetir.
- **Composición de pistas**: la captura es la imagen del visor. Si hay pistas superiores (títulos, ajustes) sobre el plano, entran en el análisis. Funciona mejor con la pista a igualar visible y sin capas encima.
- **Rango**: la LUT recorta a 0 a 1, así que no conserva súper blancos.
- **Interfaz bloqueada**: mientras se calcula, Resolve no responde (unos segundos por plano incluyendo la captura).
- **LUTs acumuladas**: cada ejecución crea archivos nuevos (con fecha y hora en el nombre) para que Resolve no use una versión en caché. Borra la carpeta `ColorMatch` de vez en cuando.
- No hay OFX ni DCTL. Una LUT por plano ya cubre el flujo completo sin compilar nada y funciona igual en gratuita y Studio; un OFX solo aportaría ajustes en tiempo real dentro del nodo, a cambio de compilar en C++ por plataforma.

## Qué está verificado y qué no

Verificado fuera de Resolve con la batería de tests (`python -m unittest discover -s tests -t .`, 81 tests):

- Igualación: sobre imágenes sintéticas con dominante de color y subexposición, el Delta E 2000 medio baja de 9,6 a menos de 2,9 con los tres métodos (alrededor de 1,3 con MKL y 0,6 con transporte óptimo), tanto aplicando la corrección directa como a través de la LUT de 33 puntos.
- Transferencia de look: el color medio se acerca a la referencia; la protección de piel reduce el cambio en tonos de piel y la de altas luces mantiene el blanco neutro.
- Casos límite: fotogramas planos (negro, gris, blanco), un solo píxel, referencia monocroma, plano monocromo, referencia plana (error claro), valores no finitos, intensidad 0 (LUT identidad), monotonía de la luminosidad y resultado determinista.
- Formato `.cube`: cabecera, 35 937 líneas, orden de los ejes, lectura de vuelta y rechazo de archivos mal formados.
- Lectura de imágenes con y sin Pillow (PNG de 8 y 16 bits con todos los filtros, PPM) y conversión de timecode (incluido drop frame 29,97 y 59,94).
- El flujo completo del script contra un Resolve simulado: planos elegidos, captura en el fotograma central con el nodo desactivado, `RefreshLUTList` antes de `SetLUT`, nodo correcto, cursor restaurado, errores por plano y compatibilidad con la API antigua.
- Las dos interfaces se construyen sin errores con objetos simulados; el instalador genera un script Python válido.

Pendiente de comprobar dentro de Resolve (no se puede automatizar sin Resolve instalado):

- Que `ExportCurrentFrameAsStill` captura el fotograma correcto tras `SetCurrentTimecode` en tu versión.
- Que `SetNodeEnabled` y `SetLUT` se comportan como documenta la API en tu versión.
- El aspecto real de la ventana UIManager y de la ventana tkinter dentro de Resolve.
- Permisos de escritura de la carpeta de LUTs en tu sistema.

## Desarrollo

```bash
python -m unittest discover -s tests -t .
```

Estructura:

- `colormatch/colorspace.py`: sRGB, Oklab, CIELAB y Delta E 2000.
- `colormatch/transfer.py`: Reinhard, MKL y transporte óptimo por cortes.
- `colormatch/protection.py`: máscaras de piel y altas luces.
- `colormatch/engine.py`: de dos fotogramas a una corrección y su LUT.
- `colormatch/lut.py`: retícula, lectura y escritura `.cube`, aplicación trilineal.
- `colormatch/workflow.py`: orquestación con la API de Resolve.
- `colormatch/ui_fusion.py`, `colormatch/ui_tk.py`, `colormatch/form.py`: interfaces.
- `colormatch/cli.py`, `colormatch/installer.py`, `resolve/ColorMatch.py`: línea de comandos, instalador y script de Resolve.
