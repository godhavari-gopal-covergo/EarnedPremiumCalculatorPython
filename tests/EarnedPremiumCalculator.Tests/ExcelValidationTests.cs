using System;
using System.Collections.Generic;

namespace EarnedPremiumCalculator.Tests;

/// <summary>
/// Tests that validate the earned premium calculator against the exact values
/// from the Excel file "Earned and Unearned Sample - Phil.xlsx".
///
/// Excel policy: Start=2026-01-01, End=2026-04-10, Premium=1250
/// PolicyDays = 2026-04-10 - 2026-01-01 = 99 days
/// DailyPremium = 1250 / 99 = 12.626262626...
/// </summary>
public class ExcelValidationTests
{
    // Rounding tolerance for decimal comparison (2 decimal places)
    private const decimal Tolerance = 0.01m;

    // ========================================================================
    // Excel scenario: Three payments, reporting for Feb 2026
    // Payments: 550 (Jan 1), 350 (Feb 1), 350 (Mar 1)
    // For Feb report: total paid as of Feb = 550 + 350 = 900
    // ========================================================================

    private static Policy ExcelMultiPayPolicy => new(
        PolicyId: "EXCEL-MULTI-PAY",
        StartDate: new DateTime(2026, 1, 1),
        EndDate: new DateTime(2026, 4, 9),   // inclusive (Excel uses 2026-04-10, but End-Start=99 means Apr 10 exclusive, so Apr 9 inclusive)
        TotalPremium: 1250m,
        BillingFrequency: BillingFrequency.Monthly
    );

    private static List<Installment> ExcelMultiPayInstallments => new()
    {
        new(1, new DateTime(2026, 1, 1), new DateTime(2026, 2, 1), 550m, InstallmentStatus.Collected),
        new(2, new DateTime(2026, 2, 1), new DateTime(2026, 3, 1), 350m, InstallmentStatus.Collected),
        new(3, new DateTime(2026, 3, 1), new DateTime(2026, 4, 1), 350m, InstallmentStatus.Billed),
    };

    [Fact]
    public void MultiPayment_Feb2026_EarnedPrior()
    {
        // Excel B18: =MIN(SUM(B9),$B$13*(B17-B3))
        // = MIN(550, 12.626263 * (2026-02-01 - 2026-01-01))
        // = MIN(550, 12.626263 * 31) = MIN(550, 391.4141...) = 391.41
        var result = EarnedPremiumCalculatorLogic.CalculateMonthlyEarnedPremium(
            ExcelMultiPayPolicy, ExcelMultiPayInstallments, 2026, 2);

        Assert.InRange(result.EarnedPrior, 391.41m - Tolerance, 391.42m + Tolerance);
    }

    [Fact]
    public void MultiPayment_Feb2026_EarnedCurrent()
    {
        // Excel B21: =MIN(($B$13*(C17-B17)),(B9+B10-B18))
        // = MIN(12.626263 * 28, 900 - 391.4141) = MIN(353.5354, 508.5859) = 353.54
        var result = EarnedPremiumCalculatorLogic.CalculateMonthlyEarnedPremium(
            ExcelMultiPayPolicy, ExcelMultiPayInstallments, 2026, 2);

        Assert.InRange(result.EarnedCurrent, 353.53m - Tolerance, 353.54m + Tolerance);
    }

    [Fact]
    public void MultiPayment_Feb2026_Unearned()
    {
        // Excel B24: =SUM(B$9,B$10)-SUM(B18,B21)
        // = 900 - 391.4141 - 353.5354 = 155.05
        var result = EarnedPremiumCalculatorLogic.CalculateMonthlyEarnedPremium(
            ExcelMultiPayPolicy, ExcelMultiPayInstallments, 2026, 2);

        Assert.InRange(result.Unearned, 155.04m - Tolerance, 155.06m + Tolerance);
    }

    // ========================================================================
    // Excel scenario: Single payment (full term), Premium=1250, fully paid
    // Rows 28–56 in the Excel
    // ========================================================================

    private static Policy ExcelSinglePayPolicy => new(
        PolicyId: "EXCEL-SINGLE-PAY",
        StartDate: new DateTime(2026, 1, 1),
        EndDate: new DateTime(2026, 4, 9),   // inclusive
        TotalPremium: 1250m,
        BillingFrequency: BillingFrequency.Annual
    );

    private static List<Installment> ExcelSinglePayInstallments => new()
    {
        new(1, new DateTime(2026, 1, 1), new DateTime(2026, 4, 10), 1250m, InstallmentStatus.Collected),
    };

    [Fact]
    public void SinglePayment_Jan2026_EarnedPrior()
    {
        // Excel B39: =B$35*(B38-B$29) = 12.626263 * (2026-01-01 - 2026-01-01) = 0.00
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 1);

        Assert.Equal(0.00m, result.EarnedPrior);
    }

    [Fact]
    public void SinglePayment_Jan2026_EarnedCurrent()
    {
        // Excel B40: =$B$35*(MIN(C38,B$30)-MIN(B38,B29))
        // = 12.626263 * (MIN(2026-02-01, 2026-04-10) - MIN(2026-01-01, 2026-01-01))
        // = 12.626263 * (2026-02-01 - 2026-01-01) = 12.626263 * 31 = 391.41
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 1);

        Assert.InRange(result.EarnedCurrent, 391.41m - Tolerance, 391.42m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Jan2026_Unearned()
    {
        // Excel B41: =B$33-(SUM(B39:B40)) = 1250 - 0 - 391.4141 = 858.59
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 1);

        Assert.InRange(result.Unearned, 858.58m - Tolerance, 858.59m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Feb2026_EarnedPrior()
    {
        // Excel B44: =B$35*(B43-B$29) = 12.626263 * 31 = 391.41
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 2);

        Assert.InRange(result.EarnedPrior, 391.41m - Tolerance, 391.42m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Feb2026_EarnedCurrent()
    {
        // Excel B45: =$B$13*(C43-B43) = 12.626263 * 28 = 353.54
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 2);

        Assert.InRange(result.EarnedCurrent, 353.53m - Tolerance, 353.54m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Feb2026_Unearned()
    {
        // Excel B46: =B$33-(SUM(B44:B45)) = 1250 - 391.41 - 353.54 = 505.05
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 2);

        Assert.InRange(result.Unearned, 505.04m - Tolerance, 505.06m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Mar2026_EarnedPrior()
    {
        // Excel B49: =B$35*(B48-B$29) = 12.626263 * 59 = 744.95
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 3);

        Assert.InRange(result.EarnedPrior, 744.94m - Tolerance, 744.95m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Mar2026_EarnedCurrent()
    {
        // Excel B50: =$B$13*(C48-B48) = 12.626263 * 31 = 391.41
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 3);

        Assert.InRange(result.EarnedCurrent, 391.41m - Tolerance, 391.42m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Mar2026_Unearned()
    {
        // Excel B51: =B$33-(SUM(B49:B50)) = 1250 - 744.95 - 391.41 = 113.64
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 3);

        Assert.InRange(result.Unearned, 113.63m - Tolerance, 113.64m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Apr2026_EarnedPrior()
    {
        // Excel B54: =B$35*(B53-B$29) = 12.626263 * 90 = 1136.36
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 4);

        Assert.InRange(result.EarnedPrior, 1136.36m - Tolerance, 1136.37m + Tolerance);
    }

    [Fact]
    public void SinglePayment_Apr2026_EarnedCurrent()
    {
        // Excel B55: =$B$13*(MIN(B30,C53)-B53)
        // = 12.626263 * (MIN(2026-04-10, 2026-05-01) - 2026-04-01)
        // = 12.626263 * 9 = 113.64
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, 4);

        Assert.InRange(result.EarnedCurrent, 113.63m - Tolerance, 113.64m + Tolerance);
    }

    [Fact]
    public void SinglePayment_AllMonths_SumToTotalPremium()
    {
        // The sum of all EarnedCurrent across all reporting months must equal TotalPremium
        decimal totalEarned = 0;
        for (int m = 1; m <= 4; m++)
        {
            var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
                ExcelSinglePayPolicy, ExcelSinglePayInstallments, 2026, m);
            totalEarned += result.EarnedCurrent;
        }

        Assert.InRange(totalEarned, 1250m - Tolerance, 1250m + Tolerance);
    }

    // ========================================================================
    // Mock data validation: 3650 premium, 365 days, 10/day
    // ========================================================================

    private static Policy MockAnnualPolicy => new(
        PolicyId: "MOCK-ANNUAL",
        StartDate: new DateTime(2026, 1, 15),
        EndDate: new DateTime(2027, 1, 14),
        TotalPremium: 3650m,
        BillingFrequency: BillingFrequency.Annual
    );

    private static List<Installment> MockAnnualInstallments => new()
    {
        new(1, new DateTime(2026, 1, 15), new DateTime(2027, 1, 15), 3650m, InstallmentStatus.Collected),
    };

    [Fact]
    public void MockAnnual_DailyRateIs10_Feb2026_Is280()
    {
        // 28 days in Feb 2026 × $10/day = $280
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            MockAnnualPolicy, MockAnnualInstallments, 2026, 2);

        Assert.Equal(280.00m, result.EarnedCurrent);
    }

    [Fact]
    public void MockAnnual_Jan2026_PartialMonth_17Days()
    {
        // Policy starts Jan 15, so only 17 days in Jan (15th to 31st) × $10 = $170
        var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            MockAnnualPolicy, MockAnnualInstallments, 2026, 1);

        Assert.Equal(170.00m, result.EarnedCurrent);
        Assert.Equal(0.00m, result.EarnedPrior);
    }

    [Fact]
    public void MockAnnual_AllMonths_SumTo3650()
    {
        decimal totalEarned = 0;
        for (int m = 1; m <= 12; m++)
        {
            var result = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
                MockAnnualPolicy, MockAnnualInstallments, 2026, m);
            totalEarned += result.EarnedCurrent;
        }
        // Add Jan 2027 (14 days)
        var jan2027 = EarnedPremiumCalculatorLogic.CalculateAnnualEarnedPremium(
            MockAnnualPolicy, MockAnnualInstallments, 2027, 1);
        totalEarned += jan2027.EarnedCurrent;

        Assert.Equal(3650.00m, totalEarned);
    }

    [Fact]
    public void MockMonthly_PaidCapKicksIn_Apr2026()
    {
        // Monthly policy: 2 months paid = 608.34
        // By Apr 2026 start: daysPrior = (Apr 1 - Jan 15) = 76 days
        // earnedPriorUncapped = 10 × 76 = 760.00 > 608.34
        // So earnedPrior = min(760, 608.34) = 608.34
        // earnedCurrent = min(10 × 30, 608.34 - 608.34) = min(300, 0) = 0
        var monthlyPolicy = new Policy("MOCK-MONTHLY", new DateTime(2026, 1, 15), new DateTime(2027, 1, 14), 3650m, BillingFrequency.Monthly);
        var installments = new List<Installment>
        {
            new(1, new DateTime(2026, 1, 15), new DateTime(2026, 2, 15), 304.17m, InstallmentStatus.Collected),
            new(2, new DateTime(2026, 2, 15), new DateTime(2026, 3, 15), 304.17m, InstallmentStatus.Collected),
        };

        var result = EarnedPremiumCalculatorLogic.CalculateMonthlyEarnedPremium(
            monthlyPolicy, installments, 2026, 4);

        Assert.Equal(608.34m, result.EarnedPrior);
        Assert.Equal(0.00m, result.EarnedCurrent);
        Assert.Equal(0.00m, result.Unearned);
    }

    [Fact]
    public void AsOfDate_Annual_Feb28_Is450()
    {
        // 45 days from Jan 15 to Feb 28 (inclusive) × $10 = $450
        var result = EarnedPremiumCalculatorLogic.CalculateAsOfDate(
            MockAnnualPolicy, MockAnnualInstallments, new DateTime(2026, 2, 28));

        Assert.Equal(450.00m, result.CumulativeEarned);
        Assert.Equal(3200.00m, result.CumulativeUnearned);
    }

    [Fact]
    public void AsOfDate_Monthly_Feb28_CappedByPaid()
    {
        // 45 days × $10 = $450 uncapped, but totalPaid = 608.34
        // min(450, 608.34) = 450 — cap doesn't kick in yet
        var monthlyPolicy = new Policy("MOCK-MONTHLY", new DateTime(2026, 1, 15), new DateTime(2027, 1, 14), 3650m, BillingFrequency.Monthly);
        var installments = new List<Installment>
        {
            new(1, new DateTime(2026, 1, 15), new DateTime(2026, 2, 15), 304.17m, InstallmentStatus.Collected),
            new(2, new DateTime(2026, 2, 15), new DateTime(2026, 3, 15), 304.17m, InstallmentStatus.Collected),
        };

        var result = EarnedPremiumCalculatorLogic.CalculateAsOfDate(monthlyPolicy, installments, new DateTime(2026, 2, 28));

        Assert.Equal(450.00m, result.CumulativeEarned);
        Assert.Equal(158.34m, result.CumulativeUnearned);
    }

    [Fact]
    public void AsOfDate_Monthly_Apr30_CappedByPaid()
    {
        // 106 days × $10 = $1060 uncapped, but totalPaid = 608.34
        // min(1060, 608.34) = 608.34 — cap kicks in
        var monthlyPolicy = new Policy("MOCK-MONTHLY", new DateTime(2026, 1, 15), new DateTime(2027, 1, 14), 3650m, BillingFrequency.Monthly);
        var installments = new List<Installment>
        {
            new(1, new DateTime(2026, 1, 15), new DateTime(2026, 2, 15), 304.17m, InstallmentStatus.Collected),
            new(2, new DateTime(2026, 2, 15), new DateTime(2026, 3, 15), 304.17m, InstallmentStatus.Collected),
        };

        var result = EarnedPremiumCalculatorLogic.CalculateAsOfDate(monthlyPolicy, installments, new DateTime(2026, 4, 30));

        Assert.Equal(608.34m, result.CumulativeEarned);
        Assert.Equal(0.00m, result.CumulativeUnearned);
    }
}
