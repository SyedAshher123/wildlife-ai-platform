import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { fetchMe, login as apiLogin, logout as apiLogout, getToken, type UserData } from './api';

interface AuthCtx {
    user: UserData | null;
    loading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthCtx>({ user: null, loading: true, login: async () => {}, logout: () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<UserData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (getToken()) {
            fetchMe().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (email: string, password: string) => {
        const u = await apiLogin(email, password);
        setUser(u);
    };

    const logout = () => {
        apiLogout();
        setUser(null);
    };

    return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
    return useContext(AuthContext);
}
