import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";
import { ChevronLeft, ChevronRight, Wallet, TrendingUp, TrendingDown, Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/integrations/api/client";
import { formatCurrency, monthName } from "@/lib/utils";

export default function Dashboard() {
  const today = new Date();
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [year, setYear] = useState(today.getFullYear());

  const { data, isLoading } = useQuery({
    queryKey: ["dashboard", month, year],
    queryFn: () => api.getDashboardSummary(month, year),
  });

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-display font-bold">Dashboard</h1>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-medium capitalize w-36 text-center">{monthName(month, year)}</span>
          <button onClick={nextMonth} className="p-1.5 rounded-lg hover:bg-white/10 transition-colors">
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="glass rounded-xl p-5"><Skeleton className="h-16 w-full" /></div>
          ))
        ) : (
          <>
            <KpiCard icon={<Wallet className="h-5 w-5 text-primary" />} label="Saldo" value={data?.balance ?? 0} color="text-foreground" />
            <KpiCard icon={<TrendingUp className="h-5 w-5 text-green-400" />} label="Receitas" value={data?.total_income ?? 0} color="text-green-400" />
            <KpiCard icon={<TrendingDown className="h-5 w-5 text-red-400" />} label="Despesas" value={data?.total_expense ?? 0} color="text-red-400" />
            <KpiCard
              icon={<Lightbulb className="h-5 w-5 text-yellow-400" />}
              label="Transações"
              value={null}
              count={data?.transaction_count ?? 0}
              color="text-yellow-400"
            />
          </>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mb-6">
        {/* Pie chart */}
        <Card className="glass border-border">
          <CardHeader>
            <CardTitle className="text-base">Despesas por Categoria</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-48 w-full" /> : (
              data?.category_breakdown.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie
                      data={data.category_breakdown}
                      dataKey="total"
                      nameKey="category_name"
                      cx="50%" cy="50%"
                      outerRadius={80}
                      label={({ category_name, percent }) =>
                        `${category_name} ${(percent * 100).toFixed(0)}%`
                      }
                      labelLine={false}
                    >
                      {data.category_breakdown.map((entry, i) => (
                        <Cell key={i} fill={entry.category_color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-muted-foreground text-sm text-center py-12">Nenhuma despesa no período</p>
              )
            )}
          </CardContent>
        </Card>

        {/* Bar chart */}
        <Card className="glass border-border">
          <CardHeader>
            <CardTitle className="text-base">Evolução Diária</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-48 w-full" /> : (
              data?.daily_evolution.length ? (
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={data.daily_evolution} margin={{ left: -20 }}>
                    <XAxis
                      dataKey="date"
                      tickFormatter={(v) => new Date(v + "T00:00:00").getDate().toString()}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip
                      labelFormatter={(v) => new Date(v + "T00:00:00").toLocaleDateString("pt-BR")}
                      formatter={(v: number, name: string) => [
                        formatCurrency(v),
                        name === "income" ? "Receita" : "Despesa",
                      ]}
                    />
                    <Bar dataKey="income" fill="#22c55e" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expense" fill="#ef4444" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-muted-foreground text-sm text-center py-12">Nenhuma transação no período</p>
              )
            )}
          </CardContent>
        </Card>
      </div>

      {/* Insight */}
      {data?.latest_insight && (
        <Card className="glass border-border">
          <CardContent className="flex gap-3 pt-5">
            <Lightbulb className="h-5 w-5 text-yellow-400 shrink-0 mt-0.5" />
            <p className="text-sm text-muted-foreground">{data.latest_insight}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
  count,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | null;
  count?: number;
  color: string;
}) {
  return (
    <div className="glass rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground font-medium">{label}</span>
        {icon}
      </div>
      {value !== null ? (
        <p className={`text-2xl font-bold ${color}`}>{formatCurrency(value)}</p>
      ) : (
        <p className={`text-2xl font-bold ${color}`}>{count}</p>
      )}
    </div>
  );
}
