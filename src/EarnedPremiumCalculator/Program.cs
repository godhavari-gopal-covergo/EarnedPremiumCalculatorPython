using System;
using System.Collections.Generic;

namespace EarnedPremiumCalculator;

public record Payment(int Number, decimal Amount, DateTime Date, bool Collected);

public record MonthlySteps(
    // Base inputs
    DateTime PolicyStart,
    DateTime PolicyEnd,
    decimal Premium,
    int PolicyDays,
    decimal DailyPremium,
    // Period
    DateTime PeriodStart,
    DateTime PeriodEnd,
    int DaysPrior,
    int DaysInPeriod,
    // Paid amounts
    decimal PaidPriorToPeriod,
    decimal TotalPaidInclPeriod,
    // Earned Prior
    decimal EarnedPriorTimeBased,
    decimal EarnedPriorPaidCap,
    decimal EarnedPrior,
    // Earned Current
    decimal EarnedCurrentTimeBased,
    decimal EarnedCurrentPaidCap,
    decimal EarnedCurrent,
    // Unearned
    decimal Unearned,
    // Product split
    decimal ProductARatio,
    decimal ProductBRatio,
    decimal ProductAEarnedPrior,
    decimal ProductBEarnedPrior,
    decimal ProductAEarnedCurrent,
    decimal ProductBEarnedCurrent,
    decimal ProductAUnearned,
    decimal ProductBUnearned
);

public static class MonthlyBillingCalculator
{
    public static MonthlySteps Calculate(
        DateTime policyStart,
        DateTime policyEnd,
        decimal premium,
        decimal productAPremium,
        decimal productBPremium,
        List<Payment> payments,
        DateTime periodStart,
        DateTime periodEnd)
    {
        // Step 1: Policy days (Excel: =B4-B3)
        int policyDays = (policyEnd - policyStart).Days;

        // Step 2: Daily premium (Excel: =B6/B12)
        decimal dailyPremium = premium / policyDays;

        // Step 3: Days prior to period (Excel: B17-B3)
        int daysPrior = (periodStart - policyStart).Days;

        // Step 4: Days in period (Excel: C17-B17)
        int daysInPeriod = (periodEnd - periodStart).Days;

        // Step 5: Paid amounts — Excel tracks which payments fall before vs. during the period
        decimal paidPriorToPeriod = 0m;
        decimal totalPaidInclPeriod = 0m;
        foreach (var p in payments)
        {
            if (!p.Collected) continue;
            if (p.Date < periodStart)
                paidPriorToPeriod += p.Amount;
            totalPaidInclPeriod += p.Amount;
        }

        // Step 6: Earned Prior (Excel Row 18: =MIN(SUM(B9), $B$13*(B17-B3)))
        //   arg1: payments collected before this period
        //   arg2: time-based earning from policy start to period start
        decimal earnedPriorTimeBased = dailyPremium * daysPrior;
        decimal earnedPriorPaidCap = paidPriorToPeriod;
        decimal earnedPrior = Math.Min(earnedPriorPaidCap, earnedPriorTimeBased);

        // Step 7: Earned Current (Excel Row 21: =MIN($B$13*(C17-B17), B9+B10-B18))
        //   arg1: time-based earning for the period
        //   arg2: total paid (incl. this period) minus already-earned prior
        decimal earnedCurrentTimeBased = dailyPremium * daysInPeriod;
        decimal earnedCurrentPaidCap = totalPaidInclPeriod - earnedPrior;
        decimal earnedCurrent = Math.Min(earnedCurrentTimeBased, Math.Max(0, earnedCurrentPaidCap));

        // Step 8: Unearned (Excel Row 24: =SUM(B9,B10)-SUM(B18,B21))
        decimal unearned = totalPaidInclPeriod - earnedPrior - earnedCurrent;

        // Step 9: Product split (Excel Rows 19-20, 22-23, 25-26)
        decimal ratioA = productAPremium / premium;
        decimal ratioB = productBPremium / premium;

        return new MonthlySteps(
            policyStart, policyEnd, premium,
            policyDays, dailyPremium,
            periodStart, periodEnd,
            daysPrior, daysInPeriod,
            paidPriorToPeriod, totalPaidInclPeriod,
            earnedPriorTimeBased, earnedPriorPaidCap, earnedPrior,
            earnedCurrentTimeBased, earnedCurrentPaidCap, earnedCurrent,
            unearned,
            ratioA, ratioB,
            earnedPrior * ratioA, earnedPrior * ratioB,
            earnedCurrent * ratioA, earnedCurrent * ratioB,
            unearned * ratioA, unearned * ratioB
        );
    }
}

public class Program
{
    // Excel uses IEEE-754 double; C# decimal is 128-bit base-10.
    // Values match within this tolerance.
    const decimal TOL = 0.0000001m;

    public static void Main(string[] args)
    {
        Console.OutputEncoding = System.Text.Encoding.UTF8;

        // ================================================================
        // INPUTS — exact values from Excel "Three Payment - One LOB-Product"
        // ================================================================
        var policyStart = new DateTime(2026, 1, 1);
        var policyEnd   = new DateTime(2026, 4, 10);
        decimal premium          = 1250m;
        decimal productAPremium  = 850m;
        decimal productBPremium  = 400m;

        var payments = new List<Payment>
        {
            new(1, 550m, new DateTime(2026, 1, 1), Collected: true),
            new(2, 350m, new DateTime(2026, 2, 1), Collected: true),
            new(3, 350m, new DateTime(2026, 3, 1), Collected: false),
        };

        var periodStart = new DateTime(2026, 2, 1);
        var periodEnd   = new DateTime(2026, 3, 1);

        // ================================================================
        // EXPECTED VALUES — copied from the Excel (data_only=True)
        // ================================================================
        decimal xl_policyDays           = 99m;
        decimal xl_dailyPremium         = 12.626262626262626m;
        decimal xl_daysPrior            = 31m;
        decimal xl_daysInPeriod         = 28m;
        decimal xl_paidPrior            = 550m;
        decimal xl_totalPaid            = 900m;
        decimal xl_earnedPriorTime      = 391.4141414141414m;    // B13*(B17-B3)
        decimal xl_earnedPriorCap       = 550m;                  // SUM(B9)
        decimal xl_earnedPrior          = 391.4141414141414m;    // Row 18
        decimal xl_earnedCurrentTime    = 353.5353535353535m;     // B13*(C17-B17)
        decimal xl_earnedCurrentCap     = 508.5858585858586m;    // B9+B10-B18 = 900-391.414
        decimal xl_earnedCurrent        = 353.5353535353535m;     // Row 21
        decimal xl_unearned             = 155.05050505050508m;   // Row 24
        decimal xl_prodA_earnedPrior    = 266.16161616161617m;   // Row 19
        decimal xl_prodB_earnedPrior    = 125.25252525252525m;   // Row 20
        decimal xl_prodA_earnedCurrent  = 240.40404040404042m;   // Row 22
        decimal xl_prodB_earnedCurrent  = 113.13131313131314m;   // Row 23
        decimal xl_prodA_unearned       = 105.43434343434346m;   // Row 25
        decimal xl_prodB_unearned       = 49.61616161616163m;    // Row 26

        // ================================================================
        // RUN THE PROGRAM CALCULATION
        // ================================================================
        var s = MonthlyBillingCalculator.Calculate(
            policyStart, policyEnd, premium,
            productAPremium, productBPremium,
            payments, periodStart, periodEnd);

        // ================================================================
        // PRINT: HEADER
        // ================================================================
        int W = 100;
        Box("MONTHLY BILLING (Three Payments) — Excel vs Program", W);
        Console.WriteLine();

        // ================================================================
        // PRINT: INPUT TABLE
        // ================================================================
        Console.WriteLine("  INPUT DATA  (from Excel Rows 3–17)");
        Console.WriteLine("  " + new string('─', W - 4));
        Input("Policy Start Date",  $"{policyStart:yyyy-MM-dd}",          "B3");
        Input("Policy End Date",    $"{policyEnd:yyyy-MM-dd} (exclusive)", "B4");
        Input("Premium",            $"{premium:N2}",                       "B6");
        Input("Product A",          $"{productAPremium:N2} (68%)",         "B7");
        Input("Product B",          $"{productBPremium:N2} (32%)",         "B8");
        Console.WriteLine("  " + new string('─', W - 4));
        Input("Payment 1",          $"{payments[0].Amount:N2}  on {payments[0].Date:yyyy-MM-dd}  (Collected)", "B9");
        Input("Payment 2",          $"{payments[1].Amount:N2}  on {payments[1].Date:yyyy-MM-dd}  (Collected)", "B10");
        Input("Payment 3",          $"{payments[2].Amount:N2}  on {payments[2].Date:yyyy-MM-dd}  (Billed)",    "B11");
        Console.WriteLine("  " + new string('─', W - 4));
        Input("Reporting Period",   $"{periodStart:yyyy-MM-dd}  to  {periodEnd:yyyy-MM-dd}  (Feb 2026)", "B17:C17");
        Console.WriteLine();

        // ================================================================
        // PRINT: STEP-BY-STEP COMPARISON TABLE
        // ================================================================
        Console.WriteLine("  STEP-BY-STEP COMPARISON");
        Console.WriteLine("  " + new string('─', W - 4));
        Console.WriteLine();

        string hdr = $"  {"#",-4} {"Step",-38} {"Excel Formula",-26} {"Excel Value",18} {"Program Value",18} {"Match",6}";
        Console.WriteLine(hdr);
        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        int pass = 0, fail = 0;

        // 1. Policy Days
        Row(ref pass, ref fail, "1",  "Policy Days",                     "=B4-B3           [B12]", xl_policyDays,          s.PolicyDays);
        Row(ref pass, ref fail, "2",  "Daily Premium",                   "=B6/B12          [B13]", xl_dailyPremium,        s.DailyPremium);
        Row(ref pass, ref fail, "3",  "Days Prior (PeriodStart-PolStart)","B17-B3                ", xl_daysPrior,           s.DaysPrior);
        Row(ref pass, ref fail, "4",  "Days in Period (PeriodEnd-Start)", "C17-B17               ", xl_daysInPeriod,        s.DaysInPeriod);
        Row(ref pass, ref fail, "5a", "Paid prior to period",            "SUM(B9)               ", xl_paidPrior,           s.PaidPriorToPeriod);
        Row(ref pass, ref fail, "5b", "Total paid incl. period",         "SUM(B9:B10)            ", xl_totalPaid,           s.TotalPaidInclPeriod);

        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        // 6. Earned Prior
        Row(ref pass, ref fail, "6a", "Earned Prior [time-based]",       "B13*(B17-B3)           ", xl_earnedPriorTime,     s.EarnedPriorTimeBased);
        Row(ref pass, ref fail, "6b", "Earned Prior [paid cap]",         "SUM(B9)          =550  ", xl_earnedPriorCap,      s.EarnedPriorPaidCap);
        Row(ref pass, ref fail, "6c", "Earned Prior = MIN(6a, 6b)",      "MIN(...)         [B18] ", xl_earnedPrior,         s.EarnedPrior);

        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        // 7. Earned Current
        Row(ref pass, ref fail, "7a", "Earned Current [time-based]",     "B13*(C17-B17)          ", xl_earnedCurrentTime,   s.EarnedCurrentTimeBased);
        Row(ref pass, ref fail, "7b", "Earned Current [paid cap]",       "B9+B10-B18             ", xl_earnedCurrentCap,    s.EarnedCurrentPaidCap);
        Row(ref pass, ref fail, "7c", "Earned Current = MIN(7a, 7b)",    "MIN(...)         [B21] ", xl_earnedCurrent,       s.EarnedCurrent);

        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        // 8. Unearned
        Row(ref pass, ref fail, "8",  "Unearned",                        "SUM(B9,B10)-SUM(B18,B21)[B24]", xl_unearned,    s.Unearned);

        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        // 9. Product split
        Row(ref pass, ref fail, "9a", "Product A — Earned Prior",        "B18*0.68         [B19] ", xl_prodA_earnedPrior,   s.ProductAEarnedPrior);
        Row(ref pass, ref fail, "9b", "Product B — Earned Prior",        "B18*0.32         [B20] ", xl_prodB_earnedPrior,   s.ProductBEarnedPrior);
        Row(ref pass, ref fail, "9c", "Product A — Earned Current",      "B21*0.68         [B22] ", xl_prodA_earnedCurrent, s.ProductAEarnedCurrent);
        Row(ref pass, ref fail, "9d", "Product B — Earned Current",      "B21*0.32         [B23] ", xl_prodB_earnedCurrent, s.ProductBEarnedCurrent);
        Row(ref pass, ref fail, "9e", "Product A — Unearned",            "B24*0.68         [B25] ", xl_prodA_unearned,      s.ProductAUnearned);
        Row(ref pass, ref fail, "9f", "Product B — Unearned",            "B24*0.32         [B26] ", xl_prodB_unearned,      s.ProductBUnearned);

        Console.WriteLine("  " + new string('─', hdr.Length - 2));

        // ================================================================
        // PRINT: SUMMARY
        // ================================================================
        Console.WriteLine();
        Box($"RESULT:  {pass} passed,  {fail} failed  out of {pass + fail} steps", W);
        Console.WriteLine();

        // ================================================================
        // PRINT: DETAILED FORMULA WALKTHROUGH
        // ================================================================
        Box("FORMULA WALKTHROUGH — Showing Substituted Values", W);
        Console.WriteLine();

        Console.WriteLine("  STEP 1: Policy Days");
        Console.WriteLine($"    Excel B12:  =B4 - B3");
        Console.WriteLine($"              = {policyEnd:yyyy-MM-dd} - {policyStart:yyyy-MM-dd}");
        Console.WriteLine($"              = {(int)xl_policyDays} days");
        Console.WriteLine($"    Program:    (policyEnd - policyStart).Days = {s.PolicyDays}");
        Console.WriteLine();

        Console.WriteLine("  STEP 2: Daily Premium");
        Console.WriteLine($"    Excel B13:  =B6 / B12");
        Console.WriteLine($"              = {premium} / {(int)xl_policyDays}");
        Console.WriteLine($"              = {xl_dailyPremium}");
        Console.WriteLine($"    Program:    premium / policyDays = {s.DailyPremium}");
        Console.WriteLine();

        Console.WriteLine("  STEP 3–4: Period Boundaries");
        Console.WriteLine($"    DaysPrior:    {periodStart:yyyy-MM-dd} - {policyStart:yyyy-MM-dd} = {s.DaysPrior} days");
        Console.WriteLine($"    DaysInPeriod: {periodEnd:yyyy-MM-dd} - {periodStart:yyyy-MM-dd} = {s.DaysInPeriod} days");
        Console.WriteLine();

        Console.WriteLine("  STEP 5: Payments");
        Console.WriteLine($"    Paid before period (only Pmt 1):  {s.PaidPriorToPeriod:N2}");
        Console.WriteLine($"    Total paid incl. period (Pmt 1+2): {s.TotalPaidInclPeriod:N2}");
        Console.WriteLine();

        Console.WriteLine("  STEP 6: Earned Prior  [Excel Row 18]");
        Console.WriteLine($"    Formula:  =MIN( SUM(B9), $B$13 * (B17 - B3) )");
        Console.WriteLine($"    arg1 (paid cap):    SUM(B9) = {s.PaidPriorToPeriod}");
        Console.WriteLine($"    arg2 (time-based):  {s.DailyPremium} * {s.DaysPrior} = {s.EarnedPriorTimeBased}");
        Console.WriteLine($"    Result:             MIN({s.PaidPriorToPeriod}, {s.EarnedPriorTimeBased})");
        Console.WriteLine($"                      = {s.EarnedPrior}");
        Console.WriteLine($"    ► Time-based ({s.EarnedPriorTimeBased:N4}) < Paid cap ({s.PaidPriorToPeriod:N2}), so time-based wins.");
        Console.WriteLine();

        Console.WriteLine("  STEP 7: Earned Current  [Excel Row 21]");
        Console.WriteLine($"    Formula:  =MIN( $B$13*(C17-B17), (B9+B10-B18) )");
        Console.WriteLine($"    arg1 (time-based):  {s.DailyPremium} * {s.DaysInPeriod} = {s.EarnedCurrentTimeBased}");
        Console.WriteLine($"    arg2 (paid cap):    {s.TotalPaidInclPeriod} - {s.EarnedPrior} = {s.EarnedCurrentPaidCap}");
        Console.WriteLine($"    Result:             MIN({s.EarnedCurrentTimeBased}, {s.EarnedCurrentPaidCap})");
        Console.WriteLine($"                      = {s.EarnedCurrent}");
        Console.WriteLine($"    ► Time-based ({s.EarnedCurrentTimeBased:N4}) < Paid cap ({s.EarnedCurrentPaidCap:N4}), so time-based wins.");
        Console.WriteLine();

        Console.WriteLine("  STEP 8: Unearned  [Excel Row 24]");
        Console.WriteLine($"    Formula:  =SUM(B9,B10) - SUM(B18, B21)");
        Console.WriteLine($"            = {s.TotalPaidInclPeriod} - ({s.EarnedPrior} + {s.EarnedCurrent})");
        Console.WriteLine($"            = {s.TotalPaidInclPeriod} - {s.EarnedPrior + s.EarnedCurrent}");
        Console.WriteLine($"            = {s.Unearned}");
        Console.WriteLine();

        Console.WriteLine("  STEP 9: Product Split");
        Console.WriteLine($"    Product A ratio = {productAPremium}/{premium} = {s.ProductARatio}");
        Console.WriteLine($"    Product B ratio = {productBPremium}/{premium} = {s.ProductBRatio}");
        Console.WriteLine($"    Product A Earned Prior   = {s.EarnedPrior} * {s.ProductARatio} = {s.ProductAEarnedPrior}");
        Console.WriteLine($"    Product B Earned Prior   = {s.EarnedPrior} * {s.ProductBRatio} = {s.ProductBEarnedPrior}");
        Console.WriteLine($"    Product A Earned Current = {s.EarnedCurrent} * {s.ProductARatio} = {s.ProductAEarnedCurrent}");
        Console.WriteLine($"    Product B Earned Current = {s.EarnedCurrent} * {s.ProductBRatio} = {s.ProductBEarnedCurrent}");
        Console.WriteLine($"    Product A Unearned       = {s.Unearned} * {s.ProductARatio} = {s.ProductAUnearned}");
        Console.WriteLine($"    Product B Unearned       = {s.Unearned} * {s.ProductBRatio} = {s.ProductBUnearned}");
        Console.WriteLine();

        // ================================================================
        // PRINT: SANITY CHECKS
        // ================================================================
        Box("SANITY CHECKS", W);
        Console.WriteLine();
        decimal sumCheck = s.EarnedPrior + s.EarnedCurrent + s.Unearned;
        Console.WriteLine($"  EarnedPrior + EarnedCurrent + Unearned = {s.EarnedPrior} + {s.EarnedCurrent} + {s.Unearned}");
        Console.WriteLine($"                                         = {sumCheck}");
        Console.WriteLine($"  TotalPaid                              = {s.TotalPaidInclPeriod}");
        Console.WriteLine($"  Match: {(sumCheck == s.TotalPaidInclPeriod ? "YES" : "NO — MISMATCH")}");
        Console.WriteLine();
        decimal prodSum = s.ProductAEarnedPrior + s.ProductBEarnedPrior
                        + s.ProductAEarnedCurrent + s.ProductBEarnedCurrent
                        + s.ProductAUnearned + s.ProductBUnearned;
        Console.WriteLine($"  Product A+B totals = {prodSum}");
        Console.WriteLine($"  TotalPaid          = {s.TotalPaidInclPeriod}");
        Console.WriteLine($"  Match: {(Math.Abs(prodSum - s.TotalPaidInclPeriod) < TOL ? "YES" : "NO — MISMATCH")}");
        Console.WriteLine();
    }

    // ────────────────────────────────────────────────────────────────
    // Helpers
    // ────────────────────────────────────────────────────────────────

    static void Box(string title, int width)
    {
        Console.WriteLine("  ╔" + new string('═', width - 4) + "╗");
        int pad = width - 4 - title.Length;
        int left = pad / 2;
        int right = pad - left;
        Console.WriteLine("  ║" + new string(' ', left) + title + new string(' ', right) + "║");
        Console.WriteLine("  ╚" + new string('═', width - 4) + "╝");
    }

    static void Input(string label, string value, string cell)
    {
        Console.WriteLine($"  {label,-24} {value,-40} ({cell})");
    }

    static void Row(ref int pass, ref int fail, string num, string name, string formula, decimal excel, decimal program)
    {
        bool match = Math.Abs(excel - program) < TOL;
        string mark = match ? "  ✓" : "  ✗";
        if (match) pass++; else fail++;

        Console.WriteLine($"  {num,-4} {name,-38} {formula,-26} {excel,18:G15} {program,18:G15} {mark,6}");

        if (!match)
        {
            Console.WriteLine($"       *** DELTA = {Math.Abs(excel - program):G10}");
        }
    }
}
