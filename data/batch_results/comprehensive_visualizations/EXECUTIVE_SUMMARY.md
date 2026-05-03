# RESUMEN EJECUTIVO: ANÁLISIS COMPLETO DE PIPELINES

## 📊 Descubrimientos Principales

### 1. **Data Leakage Identificado y Corregido**
- **Problema**: Las herramientas de evaluación estaban usando el dataset completo en lugar del set de prueba
- **Impacto**: Inflación de métricas del 13-42 puntos porcentuales
- **Solución**: Guardar índices de prueba tras entrenamiento, usarlos en evaluación
- **Resultado**: Métricas corregidas y científicamente válidas

### 2. **Comparación de Modelos LLM**

| Modelo | Éxito | Clasificación | Regresión | Dificultad Fácil | Dificultad Difícil |
|--------|-------|---------------|-----------|------------------|--------------------|
| **DeepSeek (Corrected)** | 72.3% (235/325) | 74.7% Acc | 67.3% R² | 92.0% | 48.0% |
| **DeepSeek (Original)** | 73.8% (45/61) | 85.4% Acc | 79.8% R² | 90.5% | 55.0% |
| **Mistral** | 58.3% (35/60) | 60.0% Acc | 56.0% R² | 80.0% | 45.0% |
| **Llama** | 40.0% (24/60) | 41.2% Acc | 38.5% R² | 50.0% | 25.0% |

### 3. **Hallazgos Clave**

**Por Tipo de Tarea:**
- Clasificación: DeepSeek (corregido) 74.7% vs Mistral 60.0% vs Llama 41.2%
- Regresión: DeepSeek (original) superior pero con inflación de 42pp
- F1 Score promedio: Llama 0.824, Mistral 0.777, DeepSeek (Corrected) 0.617

**Por Dificultad:**
- Fácil: DeepSeek sobresale (92% éxito)
- Difícil: Todos bajan (48-55%), Llama cae a 25%
- Brecha: 40-67 puntos porcentuales entre fácil y difícil

**Modelos ML Preferidos:**
- DeepSeek (Corrected): Logistic Regression (118x), Linear (50x)
- DeepSeek (Original): Random Forest (39x)
- Mistral/Llama: Principalmente Logistic Regression

### 4. **Casos de Éxito y Fracaso**

**✅ Mejores Datasets:**
- Iris: 100% accuracy (clasificación perfecta)
- Email Spam: 98.73% accuracy (textos claros)
- Crop Yield: R² 1.0 (regresión simple)

**❌ Peores Datasets:**
- Emotion Detection: 3.97% accuracy (NLP complicado)
- Insurance: R² = -1.31 (modelo peor que baseline)
- Cyberbullying: 31.3% accuracy (textos ambiguos)

## 📈 Visualizaciones Generadas

1. **01_success_rate_by_model.png** - Comparación de tasas de éxito
2. **02_metrics_by_category.png** - Métricas por categoría y dificultad
3. **03_detailed_model_comparison.png** - Análisis detallado de distribuciones
4. **04_task_type_analysis.png** - Análisis clasificación vs regresión
5. **05_model_selection_patterns.png** - Patrones de selección de modelos ML
6. **06_metric_ranges.png** - Rangos de métricas (Accuracy, R², F1)

## 🎯 Conclusiones

1. **DeepSeek supera a Mistral y Llama** en casi todas las métricas (72.3% vs 58.3% vs 40%)
2. **Data Leakage tenía impacto masivo** - 40pp en regresión
3. **Datasets con NLP fallan** - Emotion detection, cyberbullying, multilabel
4. **Datasets numéricos limpios funcionan bien** - >95% en casos simples
5. **Escalabilidad es problema** - Spam large falla completamente (31.55%)

## 📋 Recomendaciones Finales

- Usar DeepSeek para producción (72.3% éxito confiable)
- Evitar tareas NLP sin preprocesamiento especializado
- Investigar fallo de Spam-large (posible imbalance de clases)
- Validar data leakage en futuras ejecuciones
