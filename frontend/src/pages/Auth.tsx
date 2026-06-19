import { useEffect, useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { TrendingUp, BarChart2, Brain, Shield, Eye, EyeOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "@/components/ui/use-toast";

const BRANDING = [
  { icon: BarChart2, label: "Dashboard inteligente" },
  { icon: Brain,     label: "IA conversacional"     },
  { icon: Shield,    label: "Seguro & privado"       },
];

export default function Auth() {
  const { user, signIn, signUp } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isLogin, setIsLogin] = useState(searchParams.get("mode") !== "register");
  const [submitting, setSubmitting] = useState(false);
  const [showPass, setShowPass] = useState(false);
  const [form, setForm] = useState({ displayName: "", email: "", password: "" });

  useEffect(() => {
    if (user) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.email || !form.password) return;
    if (form.password.length < 6) {
      toast({ variant: "destructive", title: "Senha muito curta", description: "A senha deve ter ao menos 6 caracteres." });
      return;
    }
    setSubmitting(true);
    try {
      if (isLogin) {
        await signIn(form.email, form.password);
      } else {
        await signUp(form.email, form.password, form.displayName || undefined);
        toast({ title: "Conta criada!", description: "Bem-vindo ao Fluxora!" });
      }
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      toast({ variant: "destructive", title: "Erro", description: err.message ?? "Tente novamente." });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background px-4 overflow-hidden">

      {/* Glow de fundo */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full gradient-primary opacity-[0.07] blur-3xl animate-pulse-glow" />
        <div className="absolute top-0 right-0 w-[400px] h-[400px] rounded-full bg-primary/5 blur-3xl" />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md animate-fade-in">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <Link to="/" className="flex items-center gap-2 mb-3 hover:opacity-80 transition-opacity">
            <TrendingUp className="h-8 w-8 text-primary" />
            <span className="text-4xl font-display font-bold gradient-text">Fluxora</span>
          </Link>
          <p className="text-sm text-muted-foreground text-center">
            Controle financeiro com o poder da IA conversacional
          </p>

          {/* Chips de funcionalidade */}
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            {BRANDING.map(({ icon: Icon, label }) => (
              <span
                key={label}
                className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs text-primary"
              >
                <Icon className="h-3 w-3" />
                {label}
              </span>
            ))}
          </div>
        </div>

        {/* Card do formulário */}
        <div className="glass rounded-2xl border border-border p-8 shadow-2xl">
          <h1 className="text-2xl font-display font-bold mb-1">
            {isLogin ? "Bem-vindo de volta" : "Crie sua conta"}
          </h1>
          <p className="text-muted-foreground mb-6 text-sm">
            {isLogin ? "Entre com seu e-mail e senha" : "Preencha os dados para começar"}
          </p>

          <form onSubmit={handle} className="space-y-4">
            {!isLogin && (
              <div className="space-y-1.5">
                <Label htmlFor="name">Seu nome</Label>
                <Input
                  id="name"
                  placeholder="Nome completo"
                  value={form.displayName}
                  onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))}
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                placeholder="seu@email.com"
                required
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">Senha</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPass ? "text" : "password"}
                  placeholder="••••••"
                  required
                  minLength={6}
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPass((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <Button type="submit" className="w-full mt-2" disabled={submitting}>
              {submitting ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  {isLogin ? "Entrando..." : "Criando conta..."}
                </span>
              ) : isLogin ? "Entrar" : "Criar conta"}
            </Button>
          </form>

          <div className="mt-6 flex items-center gap-3">
            <div className="flex-1 h-px bg-border" />
            <span className="text-xs text-muted-foreground">ou</span>
            <div className="flex-1 h-px bg-border" />
          </div>

          <p className="mt-4 text-center text-sm text-muted-foreground">
            {isLogin ? "Não tem conta? " : "Já tem conta? "}
            <button
              onClick={() => setIsLogin((v) => !v)}
              className="text-primary hover:underline font-medium"
            >
              {isLogin ? "Cadastre-se" : "Entre"}
            </button>
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          © 2026 Fluxora · Projeto acadêmico UFG
        </p>
      </div>
    </div>
  );
}
