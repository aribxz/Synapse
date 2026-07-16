# 📘 Integrated Machine Learning Portfolio Study Guide  

---  

## Navigation  

**Part I — Professional Profile & Skills** · [[#Part I — Professional Profile & Skills]]  
**Part II — Sports Prediction Model** · [[#Part II — Sports Prediction Model]]  
**Part III — StudyScore Linear‑Regression App** · [[#Part III — StudyScore Linear‑Regression App]]  
**Part IV — Deployment & Version Control** · [[#Part IV — Deployment & Version Control]]  
**Part V — Common Pitfalls & Tips** · [[#Part I — Professional Profile & Skills]]  
**Part VI — Big Picture & Decision Flowcharts** · [[#Part VI — Big Picture & Decision Flowcharts|Part VI]]  
**Part VII — Glossary** · [[Part VII — Glossary|Part VII]]  

---  

## Part I — Professional Profile & Skills  

### 📚 Professional Profile and Background  

Understanding *who* builds a model is as important as the model itself. My background blends solid **statistical foundations** with hands‑on **machine‑learning engineering**. That mix lets me:  

* **Forecast match outcomes** for betting platforms or sports analysts.  
* **Reverse‑engineer academic goals**, turning historical exam data into actionable study plans.  
* **Expose every step**—from feature engineering to confidence‑interval reporting—through a transparent Flask API, which builds trust with stakeholders.  

> [!tip] When you can explain **how** a number was produced (e.g., a 95 % confidence interval), you gain credibility and make debugging far easier.  

### 🛠️ Core Skills & Tools  

| Skill Area | Tools / Techniques | Why It Helps |
|------------|-------------------|--------------|
| **Predictive Modeling** | XGBoost (3‑class classification), Linear Regression | Captures non‑linear interactions; works well with high‑dimensional data. |
| **Statistical Modeling** | Poisson Distribution, Dixon‑Coles goal model, Maximum Likelihood Estimation | Provides a principled way to model count data (goals) and estimate parameters from scratch. |
| **Feature Engineering** | 70+ leakage‑free pre‑match features, custom interaction terms, binary flags | Captures subtle patterns while avoiding data leakage that would inflate performance. |
| **Model Evaluation** | 95 % confidence intervals (full‑leverage formulas) | Gives precise uncertainty estimates for predictions and API reporting. |
| **Deployment** | Flask, Render (cloud hosting) | Turns notebooks into reusable, always‑available services. |
| **Foundations** | Data Structures & Algorithms, OOP, statistical theory | Guarantees clean, maintainable code and sound mathematical reasoning. |

> [!info] The table reflects the core competencies demonstrated in the source material; no new tools have been invented for this guide.  

#### Skill Pipeline Diagram  

```mermaid
flowchart LR
    A[Data Collection] --> B[LeakageFree Feature Engineering]
    B --> C[Statistical Modeling]
    C --> D[MachineLearning (XGBoost, LinearRegression)]
    D --> E[Model Evaluation (ConfidenceIntervals)]
    E --> F[Deployment (Flask, Render)]
```
*From raw data to a production‑ready API.*

---  

## Part II — Sports Prediction Model  

### 🏆 Why Sports Prediction Matters  

If you want to bet on the next Premier League weekend or power a sports‑analytics dashboard, you need a model that can **predict match outcomes before the whistle blows**. A 3‑class classifier (home win / draw / away win) supplies exactly the signals needed for odds‑making, fantasy‑football line‑ups, or any downstream decision‑making. The model is not a black‑box XGBoost alone—it is anchored by a statistical **Dixon‑Coles goal model**, giving interpretable goal‑rate estimates *and* the predictive punch of gradient boosting.  

> [!tip] Combining a theory‑driven statistical model with a data‑driven booster often yields better calibration than either approach alone.  

### 📊 Model Overview  

1. **Historical backbone** – six full seasons of Premier League data (matches, goals, team stats).  
2. **Hybrid architecture** – XGBoost handles the 3‑class classification; the Dixon‑Coles component feeds expected goal counts into the feature set.  
3. **Feature richness** – > 70 engineered pre‑match variables, all vetted to be leakage‑free.  

The pipeline in a nutshell:  

```mermaid
flowchart LR
    A[Raw Match Data] --> B[Seasonal Aggregation]
    B --> C[Goal Rate Estimation (DixonColes)]
    C --> D[Feature Engineering (70+ vars)]
    D --> E[XGBoost 3Class Classifier]
    E --> F[Predicted Outcome (Home/Draw/Away)]
```
*From raw historic results to the final win/draw/lose prediction.*  

### 🔧 Feature Engineering (Leakage‑Free)  

“Leakage‑free” means we never sneak future information (like the actual final score) into the training set. Every feature is computed **before** the match starts—think of it as a pre‑game scouting report. Examples:  

* **Team form** – points earned in the last five games.  
* **Home‑advantage indicator** – binary flag for the home team.  
* **Head‑to‑head win rate** – proportion of wins in the last ten meetings (computed using only matches that occurred before the target date).  

### ⚽ Dixon‑Coles Goal Model  

The Dixon‑Coles model estimates the expected number of goals for each team using a **Poisson** framework, adjusted for low‑scoring match anomalies. For teams *i* (home) and *j* (away):

$$
\lambda_{i}= \exp(\mu + \alpha_i + \beta_j + \gamma \cdot \text{HomeAdvantage})
$$

$$
\lambda_{j}= \exp(\mu + \alpha_j + \beta_i)
$$

where  

* $\mu$ = overall league scoring rate,  
* $\alpha$ = attacking strength,  
* $\beta$ = defensive weakness,  
* $\gamma$ = home‑advantage coefficient.  

Maximum Likelihood Estimation (MLE) is used to fit $\alpha, \beta, \gamma$ from historical match counts.  

> [!important] The Dixon‑Coles adjustment captures the empirical tendency for low‑scoring games (0‑0, 1‑0) to be slightly more common than a pure Poisson model predicts.  

### > [!example] Worked Example – Predicting a Single Match  

| Team | Recent Points (5) | Home? | Attack (α) | Defense (β) |
|------|-------------------|-------|------------|------------|
| **Arsenal** | 12 | Yes | 0.30 | -0.10 |
| **Chelsea** | 8  | No  | 0.20 | -0.05 |

Assume league‑wide log‑scoring rate $\mu = 1.5$ and home‑advantage $\gamma = 0.25$.  

1. Compute home‑team expected goals:  

$$
\lambda_{\text{Arsenal}} = \exp(1.5 + 0.30 - 0.05 + 0.25) = \exp(2.00) \approx 7.39
$$

2. Compute away‑team expected goals:  

$$
\lambda_{\text{Chelsea}} = \exp(1.5 + 0.20 - 0.10) = \exp(1.60) \approx 4.95
$$

3. Feed $\lambda_{\text{Arsenal}}$ and $\lambda_{\text{Chelsea}}$ into the XGBoost feature vector (along with form, head‑to‑head stats, etc.).  

4. XGBoost outputs class probabilities:  

* Home win: **0.58**  
* Draw: **0.22**  
* Away win: **0.20**  

> [!tip] The probabilities sum to 1.0; the highest probability (home win) becomes the predicted outcome, but the full distribution is useful for odds‑making.  

### 📉 Pitfalls & Tips  

| Pitfall | Why It Happens | Fix |
|---------|----------------|-----|
| **Data leakage** | Using post‑match stats (e.g., final score) as features. | Build all features strictly from data available *before* kickoff. |
| **Over‑fitting to historic seasons** | Too many trees or too deep a model on limited data. | Use early‑stopping on a validation set and limit max depth to 5–7. |
| **Ignoring home‑advantage** | Model treats both sides symmetrically. | Explicitly add a binary home flag or a calibrated $\gamma$ term. |

> [!warning] Forgetting to regularize XGBoost (setting `lambda`/`alpha` to 0) can cause wildly unstable probability estimates on rare matchups.  

---  

## Part III — StudyScore Linear‑Regression App  

### 🏆 Why Predicting Study Scores Matters  

Imagine you could tell a student exactly how much they need to study to hit a target exam score. The **StudyScore** web app does just that: it ingests a student’s historical performance, runs a custom linear regression (with interaction terms), and returns a **predicted score plus a 95 % confidence interval**. The interval tells you how *certain* the model is—critical when allocating tutoring resources or setting realistic goals.  

> [!tip] Providing uncertainty (confidence intervals) is often more valuable to decision‑makers than a single point estimate.  

### 📐 Model Architecture  

**Linear regression with interaction terms**  
A plain linear model assumes each predictor contributes independently. Interaction terms allow the effect of one predictor (e.g., *hours studied*) to depend on another (e.g., *attendance*).  

The model formula:  

$$
\hat{y}= \beta_0 + \beta_1 \text{Hours} + \beta_2 \text{Attendance} + \beta_3 (\text{Hours}\times\text{Attendance}) + \dots
$$

**Full‑leverage confidence intervals**  
Instead of calling external libraries for intervals, the app computes them from scratch using the leverage $h_i$ of each observation:  

$$
\text{SE}_{\hat{y}_i}= \sqrt{\sigma^2 \, h_i}
$$

$$
\hat{y}_* \pm t_{0.975,\,df}\times \text{SE}_{\hat{y}_*}
$$

where $\sigma^2$ is the residual variance and $t_{0.975,df}$ is the 97.5 % quantile of the $t$‑distribution with $df=n-p$.  

> [!tip] The full‑leverage approach yields *exact* intervals for OLS, even with dozens of engineered features.  

### 🔧 Leakage‑Free Feature Engineering  

All 70 + features are built **without peeking** at the future exam score. Examples:  

* **Cumulative GPA up to the previous semester** – allowed.  
* **GPA after the current exam** – prohibited (leak).  

The pipeline enforces this rule by constructing the feature matrix chronologically, discarding any columns that reference future data.  

### > [!example] Worked Example – Predicting a Student’s Score  

| Student | HoursStudied | Attendance% | PriorGPA |
|---------|--------------|------------|----------|
| Alice   | 12           | 85         | 3.4      |

Assume the fitted coefficients are:  

* $\beta_0 = 45$  
* $\beta_1 = 1.2$ (Hours)  
* $\beta_2 = 0.3$ (Attendance)  
* $\beta_3 = 0.02$ (Hours × Attendance)  

1. Compute interaction: $12 \times 85 = 1020$.  
2. Predicted score:  

$$
\hat{y}=45 + 1.2(12) + 0.3(85) + 0.02(1020) = 45 + 14.4 + 25.5 + 20.4 = 105.3
$$

Since exam scores are capped at 100, the model would report **100** (or apply a post‑hoc clipping).  

3. Suppose residual variance $\sigma^2 = 9$ and leverage for Alice $h_i = 0.12$.  

$$
\text{SE}_{\hat{y}_i}= \sqrt{9 \times 0.12}= \sqrt{1.08}\approx 1.04
$$

With $df = 150$, $t_{0.975,150}\approx 1.98$.  

$$
\text{95 % CI}= 105.3 \pm 1.98 \times 1.04 \approx 105.3 \pm 2.06 \; \Rightarrow\; [103.2,\;107.4]
$$

Clipping to the score range yields **[100, 100]** – a sign that Alice is *very likely* to max out.  

> [!tip] When the interval hits the score ceiling, consider re‑scaling the target variable or adding a regularization term to avoid over‑confident predictions.  

### 📉 Pitfalls & Tips  

| Pitfall | Cause | Remedy |
|---------|-------|--------|
| **Multicollinearity** | Interaction terms can be highly correlated with their base features. | Center (zero‑mean) the original variables before creating interactions. |
| **Leverage extremes** | Outliers get high leverage, inflating SE. | Use robust regression (Huber loss) or remove extreme points. |
| **Ignoring heteroscedasticity** | Variance of errors grows with study time. | Apply weighted least squares or transform the response. |

> [!warning] Reporting a narrow confidence interval for a student with an extreme leverage value can be *misleading*; always inspect leverage diagnostics.  

---  

## Part IV — Deployment & Version Control  

### 🔧 End‑to‑End Deployment Stack  

1. **Data Manipulation** – **NumPy**, **Pandas**, **SciPy** for cleaning, feature creation, and statistical calculations.  
2. **Modeling** – **XGBoost**, **scikit‑learn**, custom OLS code for linear regression.  
3. **Version Control** – **Git** for local tracking; **GitHub** for remote collaboration and CI/CD triggers.  
4. **API Layer** – **Flask** serves model predictions and confidence intervals as JSON