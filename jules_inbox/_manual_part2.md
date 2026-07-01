
---

## Chapter 6: Depth of Market (DOM) & Visual Order Entry

The Depth of Market (DOM), also known as the price ladder, is the central execution interface for short-term traders. It displays the pending limit orders (liquidity) at each price level above and below the current market price.

### The DOM Trader Interface

Quantower's DOM Trader provides a high-performance price ladder with one-click execution:

```
+-----------------------------------------------------------+
| DOM TRADER                                                |
+-----------------------------------------------------------+
| Price    | Bid Size | Ask Size | MBO Queue   | Trade      |
+----------+----------+----------+-------------+------------+
| 5000.75  |          | 240      | [Order #1]  | SELL       |
| 5000.50  |          | 185      | [Order #2]  | SELL       |
| 5000.25  |          | 95       | [Order #3]  | SELL       |
+----------+----------+----------+-------------+------------+
| 5000.00  | [ LAST TRADE PRICE: 5000.00 ]                  |
+----------+----------+----------+-------------+------------+
| 4999.75  | 110      |          | [Order #4]  | BUY        |
| 4999.50  | 190      |          | [Order #5]  | BUY        |
| 4999.25  | 320      |          | [Order #6]  | BUY        |
+-----------------------------------------------------------+
```

- **Bid Size Column:** Displays buy limit orders.
- **Ask Size Column:** Displays sell limit orders.
- **MBO Column:** Itemizes individual order queue sizes at each price level, allowing traders to see if a level is dominated by one large institutional order or many small retail orders.
- **Trade Buttons:** One-click execution. Left-clicking the Bid Size column places a Buy Limit. Left-clicking the Ask Size column places a Sell Limit. Right-clicking places Stop orders.

### DOM Surface: 3D Liquidity Heatmap

The DOM Surface is an advanced analytical panel that records the historical changes in the order book. It plots limit orders as a color-coded heatmap over time:

- **Bright Colors (e.g., Red, Orange):** Represent high-volume limit blocks (large resting orders). These act as magnet zones or strong support/resistance barriers, as price requires significant aggressive volume to break through them.
- **Cool Colors (e.g., Blue, Black):** Represent thin liquidity. Price can move quickly through these zones due to lack of passive resistance.

**Analyzing Order Book Dynamics:**

- **Spoofing / Pulling:** Large limit orders that appear as price approaches, then disappear before execution. DOM Surface tracks this by showing short, thick horizontal lines that vanish before being touched.
- **Absorption:** A bright horizontal band (huge resting limit) that price attacks repeatedly but fails to break, while aggressive trades print on the tape. This indicates a large player is absorbing the market flow.

---

## Chapter 7: Volumetric Analysis & Order Flow Trading

While standard charts display what happened to price, volumetric tools display how it happened. They reveal the internal transactions within each candle, helping traders identify imbalances, institutional involvement, and turning points.

### Cluster Chart (Footprint Chart)

A cluster chart decomposes each candle into horizontal price segments, displaying the exact volume executed on the Bid (market sellers) versus the Ask (market buyers).

#### Single, Double, and Imbalance Views

- **Single Cluster:** Displays one metric per price level inside the bar (e.g., Total Volume or Net Delta).
- **Double Cluster:** Displays two metrics side-by-side (e.g., Volume on the left, Delta on the right). This is useful for verifying both the intensity of trading and the net market bias.
- **Imbalance View:** The industry standard for footprint trading. It compares buying volume on the Ask of a price level diagonally against selling volume on the Bid of the price level below it.

**Diagonal Comparison:** Buyers lift the Ask diagonally, while sellers hit the Bid diagonally:

```
Price level N+1: [ Bid Volume (N+1) ] \   / [ Ask Volume (N+1) ]
                                      X
Price level N  : [ Bid Volume (N)   ] /   \ [ Ask Volume (N)   ]
```

**Imbalance Ratio:** If Ask Volume (N+1) exceeds Bid Volume (N) by a specified ratio (e.g., 3:1 or 300%), the Ask volume is highlighted in bright green as an aggressive buying imbalance. If Bid Volume (N) exceeds Ask Volume (N+1) by the same ratio, the Bid volume is highlighted in bright red as an aggressive selling imbalance.

#### Key Order Flow Concepts

- **Absorption:** Occurs when aggressive market orders attack a price level but fail to move the price because of a large passive limit order. This appears on a footprint chart as a large buying imbalance (on the Ask) at the very top of a bullish candle, but the candle fails to close higher. This signals a potential bearish reversal.
- **Exhaustion:** Occurs when aggressive volume dries up as price reaches a key level. This appears on a footprint chart as extremely low volume (e.g., 0 or 1 contract) on the Ask at the top of a candle, indicating buyers are unwilling to bid higher.
- **Stacked Imbalances:** Occur when three or more consecutive price levels within a single candle show buying or selling imbalances. This indicates high institutional conviction and serves as a strong support or resistance zone for future retests.

### Volume Profile

A Volume Profile is a horizontal histogram that plots the distribution of traded volume across price levels over a specified period.

```
+-----------------------------------------------------------+
| VOLUME PROFILE                                            |
+-----------------------------------------------------------+
| Price    | Volume Histogram                               |
+----------+------------------------------------------------+
| 5005.00  | ####                                           |
| 5004.00  | ########                                       |
| 5003.00  | ############## (Value Area High - VAH)         |
| 5002.00  | ##############################                 |
| 5001.00  | ##########################################(POC)|
| 5000.00  | ###########################                    |
| 4999.00  | ############ (Value Area Low - VAL)            |
| 4998.00  | #####                                          |
+-----------------------------------------------------------+
```

- **Point of Control (POC):** The exact price level where the highest volume was traded during the selected session. It represents the ultimate "fair value" or equilibrium point.
- **Value Area (VA):** The price range where a specified percentage (usually 70%) of total volume was traded. It represents the zone of high acceptance.
- **Value Area High (VAH):** The upper boundary of the Value Area.
- **Value Area Low (VAL):** The lower boundary of the Value Area.
- **High-Volume Nodes (HVN):** Price levels where significant trading occurred. These act as support or resistance, as market participants are comfortable trading at these prices.
- **Low-Volume Nodes (LVN):** Price levels where very little volume was traded. Price moves quickly through these zones due to lack of interest or liquidity, creating sharp rejection points.

### Cumulative Volume Delta (CVD)

CVD is a running total of the differences between aggressive buying (market buys) and aggressive selling (market sells) over a specified period:

$$\text{CVD} = \sum (\text{Ask Volume} - \text{Bid Volume})$$

**Trading Divergences:**

- **Bullish Divergence:** Price makes a new lower low, but the CVD line makes a higher low. This indicates that market sellers are aggressively hitting the bid, but a passive buyer is absorbing their orders. This is a strong bullish reversal signal.
- **Bearish Divergence:** Price makes a new higher high, but CVD makes a lower high. This indicates aggressive buyers are lifting the Ask, but a passive institutional seller is absorbing their flow. This is a bearish reversal signal.

### Volume Weighted Average Price (VWAP)

VWAP represents the average price of an asset weighted by its traded volume over a specified period. It is the benchmark used by institutional algorithms to execute large orders without causing market impact:

$$\text{VWAP} = \frac{\sum (\text{Price} \times \text{Volume})}{\sum \text{Volume}}$$

**Standard Deviation Bands:** Plots 1st, 2nd, and 3rd standard deviation bands around the VWAP line. Intraday price tends to stay within the 2nd standard deviation band 95% of the time. Retests of these outer bands are treated as high-probability mean-reversion setups.

### Time Price Opportunity (TPO) & Market Profile

The TPO Profile, also known as Market Profile, structures the market session by tracking price distribution over time rather than volume.

- **Letters as Time Segments:** Each 30-minute interval of the trading session is assigned a letter (A for the first 30 mins, B for the next, etc.).
- **Value Area and POC:** Similar to Volume Profile, TPO identifies the Point of Control (where price spent the most time) and the Value Area.
- **Profile Shapes:**
  - **Normal Day / Bell Curve:** Balanced market with an active value area.
  - **P-Shape:** Occurs when the market rallies rapidly during the first half of the session and then consolidates at the top. This indicates short covering and a potential trend pause.
  - **b-Shape:** Occurs when the market falls sharply early in the session and consolidates at the bottom, indicating long liquidation.

---

## Chapter 8: Strategy Manager & Historical Backtester

Quantower provides two integrated modules for automated trading: the Strategies Manager (for live strategy execution) and the Backtest & Optimize panel (for historical performance analysis).

### The Backtester Engine

The Backtest & Optimize panel is designed to evaluate C# strategies against historical data before deployment.

```
+-----------------------------------------------------------+
| BACKTEST & OPTIMIZE                                       |
+-----------------------------------------------------------+
| [Strategy Select] -> "OrderFlowBreakout"                  |
| [Symbol] -> "NQ September 2026"                           |
| [Date Range] -> "2026-01-01 to 2026-06-20"                |
| [History Type] -> Tick-by-Tick (Accurate)                 |
| [Execution Engine]                                        |
|   |-- Commisssions: $2.40 per side                        |
|   |-- Slippage: [ 1 Tick ] (Conservative)                 |
| [Run Optimize] -> Sweeps parameters using Genetic           |
|                   selection algorithms.                     |
+-----------------------------------------------------------+
```

- **History Type:** Selecting the correct data granularity is critical. While M1 (1-minute bars) is fast, it can produce unrealistic backtesting results. Tick-by-Tick history is necessary for order flow and DOM-based strategies, as it replicates the exact order of transactions inside each candle.
- **Slippage Simulation:** Slippage represents the difference between your requested entry price and the actual execution price. Setting slippage to 1 or 2 ticks ensures that backtest results are realistic.
- **Optimization Engine:** Implements genetic optimization algorithms. This allows developers to sweep multiple parameter ranges (e.g., testing moving average periods from 10 to 200 in steps of 5) to locate the highest-performing configurations without curve-fitting.

**Critical operator distinction:** Strategy Manager (StM) = live/paper/replay runtime. Backtest & Optimize = historical simulation only. Do not confuse them.

---

## Chapter 9: Visual Studio 2022 Setup & C# Algo Environment

Quantower Algo is the integrated development ecosystem for building custom indicators and automated trading strategies using C# and Microsoft .NET Core.

### Setting Up the Environment

To begin development, you must install Visual Studio and the Quantower Algo Extension:

1. **Download Visual Studio 2022:** Download the free Community edition from Microsoft's official website.
2. **Select Workloads:** During installation, select .NET desktop development in the workloads panel. This installs the required MSBuild compiler tools and libraries.
3. **Install the Quantower Algo Extension:** Open Visual Studio 2022. Navigate to Extensions -> Manage Extensions from the main menu. Select the Online tab, search for Quantower, and download the extension. Restart Visual Studio to complete the installation.

### Creating a New Project

1. Open Visual Studio 2022 and click Create a new project.
2. Type Quantower in the template search box.
3. You will see several templates: Quantower Indicator (for building custom visual indicators) and Quantower Strategy (for building custom automated strategies).
4. Select Quantower Strategy, enter a project name (e.g., TIB_Capital_Terminal), and click Create.

### Anatomy of a Quantower Algo Project

The created project has a structured layout:

- **TIB_Capital_Terminal.csproj:** The project configuration file. It references the required assemblies and targets .NET 6.0 or .NET 7.0, depending on your Quantower installation.
- **Assembly References:** The extension automatically references the core Quantower DLLs located in the local platform directory:
  - `TradingPlatform.BusinessLayer.dll`: The primary namespace containing all business objects (Core, Symbol, Account, Order, Position).
  - `TradingPlatform.BusinessLayer.Chart.dll`: Contains classes for drawing custom shapes, text, and rendering elements directly onto the chart.

---

## Chapter 10: Quantower C# API Fundamentals

Developing successful automated trading systems requires a solid understanding of the primary classes and business objects exposed by the Quantower C# API.

### The Core Class (TradingPlatform.BusinessLayer.Core)

The Core class is the central entry point for the API. It is accessed via the static property `Core.Instance`. It manages all connections, symbols, accounts, and active orders.

```csharp
// Access active broker connections
var connections = Core.Instance.Connections;

// Retrieve a specific symbol from the cache or broker
Symbol symbol = Core.Instance.GetSymbol("NQ_September_2026");

// Retrieve your active trading account
Account account = Core.Instance.Accounts.FirstOrDefault();
```

### The Symbol Class (TradingPlatform.BusinessLayer.Symbol)

The Symbol class represents a specific financial instrument. It provides access to real-time quotes, contract specifications, and historical data.

```csharp
string symbolName = symbol.Name;
double currentBid = symbol.Bid;
double currentAsk = symbol.Ask;
double tickSize = symbol.TickSize; // e.g., 0.25 for ES futures
double pointSize = symbol.PointSize;
```

### Requesting Historical Data

The Quantower API provides robust, asynchronous methods to request historical price data. Developers can request traditional time-based bars or tick-level history:

```csharp
// Download 15-minute bars for the last 30 days
IHistoricalData historicalData = symbol.GetHistory(
    Period.MIN15,
    HistoryType.Bid,
    DateTime.UtcNow.AddDays(-30),
    DateTime.UtcNow
);

// Iterate through bars
for (int i = 0; i < historicalData.Count; i++)
{
    var bar = (HistoryItemBar)historicalData[i];
    double openPrice = bar.Open;
    double closePrice = bar.Close;
    long volume = bar.Volume;
}
```
