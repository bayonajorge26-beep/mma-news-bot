# 🥊 Bot Deportes de Combate España — Telegram

Monitoriza en tiempo real UFC, Boxeo mundial, La Velada del Año, Jordi Wild, KSI y peleadores españoles.
Traduce automáticamente al español con IA y envía solo lo relevante a tu grupo de Telegram.

---

## 📡 Qué cubre el bot

### 🏆 MMA / UFC
| Fuente | Tipo |
|--------|------|
| MMA Fighting, MMA Junkie, Bloody Elbow | RSS directo |
| UFC.com, Sherdog | RSS directo |
| PFL / Bellator | RSS directo |
| AS MMA, Google News MMA España | RSS / búsqueda |

### 🥊 Boxeo
| Fuente | Tipo |
|--------|------|
| Boxing Scene, The Ring, ESPN Boxing | RSS directo |
| Bad Left Hook, Marca Boxeo, AS Boxeo | RSS directo |
| Google News boxeo español | Búsqueda |

### 🎮 Streamers & Creadores
| Evento | Rastreo |
|--------|---------|
| La Velada del Año (Ibai) | Google News RSS |
| Jordi Wild / The Wild Project | Google News RSS |
| KSI, Logan Paul, Jake Paul | Google News RSS |

> Solo se envían noticias con pelea confirmada, resultado o KO. Sin ruido.

---

## 🇪🇸 Peleadores siempre monitorizados

**MMA España (estrellas + promesas)**
- Ilia Topuria · Ángel Pascual · Askar Mozharov
- Jesús Paredes · Roberto Soldic · Marc Diakiese
- Cualquier noticia con "peleador español en UFC", "promesa española"...

**Boxeo España**
- Kerman Lejarraga · Jon Fernández · Samuel Carmona
- José Quiles · Sándor Martin · Gabriel Escobar · Edgar Berlanga

**Boxeo hispano (muy seguidos en España)**
- Canelo Álvarez · Ryan García · Lomachenko · Usyk

---

## 📩 Formato de mensajes

```
🏆 UFC/MMA 🇪🇸
*Topuria defiende el cinturón ante Holloway en UFC 317*

El campeón peso pluma confirmó la pelea para julio en Las Vegas…

🔗 Leer más
```

```
🎮 Velada 🎥
*Ibai confirma la pelea estelar de La Velada 5*

El streamer bilbaíno anunció el combate principal con fecha…

🔗 Leer más
```

---

## ⚙️ Setup en 10 minutos

### 1. Crear bot en Telegram
- Habla con **@BotFather** → `/newbot` → guarda el token

### 2. Obtener Chat ID del grupo
- Añade el bot al grupo como admin
- Ve a: `https://api.telegram.org/bot<TOKEN>/getUpdates`
- Busca `"chat":{"id":` → ese número negativo es tu Chat ID

### 3. API Key de Anthropic (traducción)
- [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key

### 4. Deploy en Railway
1. Sube a GitHub
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Añade estas variables:

| Variable | Valor |
|----------|-------|
| `TELEGRAM_TOKEN` | Token del bot |
| `TELEGRAM_CHAT_ID` | ID negativo del grupo |
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `CHECK_INTERVAL` | `900` (opcional, 15 min) |

---

## 🔧 Añadir un peleador español nuevo

En `src/bot.py`, busca `SPANISH_FIGHTERS_KNOWN` y añade:
```python
"nombre apellido",
"apodo del peleador",
```

## 💰 Coste estimado mensual
| Servicio | Coste |
|----------|-------|
| Railway | Gratis (500h/mes) |
| Anthropic API (Haiku) | ~0.50–2€/mes |

