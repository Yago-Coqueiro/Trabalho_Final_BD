import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  TrendingUp,
  BarChart2,
  MessageSquare,
  Tag,
  Activity,
  Shield,
  Zap,
  Clock,
  CheckCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";

const FEATURES = [
  { icon: BarChart2, title: "Dashboard Inteligente", desc: "Visualize receitas, despesas e saldo em tempo real com gráficos interativos." },
  { icon: Zap, title: "IA que Categoriza", desc: "Nosso assistente identifica automaticamente a categoria de cada transação." },
  { icon: MessageSquare, title: "Chat com IA", desc: "Converse naturalmente para registrar gastos, consultar saldo e definir metas." },
  { icon: Tag, title: "Controle por Categorias", desc: "Organize seus gastos em categorias personalizadas com cores e ícones." },
  { icon: Activity, title: "Evolução Diária", desc: "Acompanhe o fluxo de receitas e despesas dia a dia ao longo do mês." },
  { icon: Shield, title: "Segurança Total", desc: "Seus dados são protegidos com autenticação JWT e armazenamento seguro." },
];

const METRICS = [
  { value: "10k+", label: "Usuários ativos" },
  { value: "R$50M+", label: "Organizados" },
  { value: "98%", label: "Satisfação" },
  { value: "2min", label: "Para começar" },
];

const STEPS = [
  { num: "01", title: "Crie sua conta", desc: "Cadastre-se gratuitamente em menos de 2 minutos." },
  { num: "02", title: "Converse com a IA", desc: 'Diga ao assistente seus gastos e receitas em linguagem natural: "Gastei R$50 no mercado".' },
  { num: "03", title: "A IA organiza tudo", desc: "O assistente registra, categoriza e gera insights sobre suas finanças automaticamente." },
];

export default function Index() {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const scrollToFeatures = () => {
    document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 glass border-b border-border">
        <div className="mx-auto max-w-6xl px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-6 w-6 text-primary" />
            <span className="text-xl font-display font-bold gradient-text">Fluxora</span>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link to="/auth">Entrar</Link>
            </Button>
            <Button asChild>
              <Link to="/auth?mode=register">Criar Conta</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4 text-center relative overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-20 left-1/2 -translate-x-1/2 w-[600px] h-[600px] rounded-full gradient-primary opacity-10 blur-3xl animate-pulse-glow" />
        </div>
        <div className="relative mx-auto max-w-3xl animate-fade-in">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary mb-6">
            <Zap className="h-3.5 w-3.5" />
            Controle financeiro com IA
          </div>
          <h1 className="text-5xl md:text-6xl font-display font-bold leading-tight mb-6">
            Suas finanças no piloto{" "}
            <span className="gradient-text">automático</span>
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-xl mx-auto">
            Gerencie receitas, despesas e metas conversando com um assistente financeiro inteligente. Sem planilhas, sem complicação.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button size="lg" asChild>
              <Link to="/auth?mode=register">Comece Grátis</Link>
            </Button>
            <Button size="lg" variant="outline" onClick={scrollToFeatures}>
              Saiba Mais
            </Button>
          </div>
        </div>
      </section>

      {/* Metrics */}
      <section className="py-12 px-4 border-y border-border">
        <div className="mx-auto max-w-4xl grid grid-cols-2 md:grid-cols-4 gap-6">
          {METRICS.map(({ value, label }) => (
            <div key={label} className="text-center">
              <div className="text-3xl font-bold gradient-text">{value}</div>
              <div className="text-sm text-muted-foreground mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-3xl font-display font-bold text-center mb-12">
            Tudo que você precisa para <span className="gradient-text">controlar suas finanças</span>
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="glass rounded-xl p-6 hover:border-primary/30 transition-colors">
                <div className="h-10 w-10 rounded-lg gradient-primary flex items-center justify-center mb-4">
                  <Icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold mb-2">{title}</h3>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-4 border-y border-border">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-3xl font-display font-bold text-center mb-12">
            Como <span className="gradient-text">funciona</span>
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            {STEPS.map(({ num, title, desc }) => (
              <div key={num} className="text-center">
                <div className="text-5xl font-bold gradient-text mb-4">{num}</div>
                <h3 className="font-semibold mb-2">{title}</h3>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-20 px-4">
        <div className="mx-auto max-w-4xl grid md:grid-cols-3 gap-6">
          {[
            { icon: CheckCircle, title: "Sem planilhas", desc: "Esqueça as planilhas complicadas. Converse naturalmente com a IA." },
            { icon: Clock, title: "Economize tempo", desc: "Registre gastos em segundos, sem digitar em formulários." },
            { icon: Zap, title: "Tudo automático", desc: "Categorização, insights e resumos gerados automaticamente pela IA." },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="glass rounded-xl p-6 text-center">
              <Icon className="h-8 w-8 text-primary mx-auto mb-4" />
              <h3 className="font-semibold mb-2">{title}</h3>
              <p className="text-sm text-muted-foreground">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Final */}
      <section className="py-20 px-4 text-center gradient-primary">
        <h2 className="text-3xl font-display font-bold text-white mb-4">
          Pronto para começar?
        </h2>
        <p className="text-white/80 mb-8">Crie sua conta grátis e assuma o controle das suas finanças hoje.</p>
        <Button size="lg" variant="secondary" asChild>
          <Link to="/auth?mode=register">Criar conta grátis</Link>
        </Button>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-border text-center text-sm text-muted-foreground">
        <div className="flex items-center justify-center gap-2 mb-3">
          <TrendingUp className="h-4 w-4 text-primary" />
          <span className="font-bold gradient-text">Fluxora</span>
        </div>
        <p>© 2026 Fluxora. Projeto acadêmico — UFG Banco de Dados.</p>
      </footer>
    </div>
  );
}
