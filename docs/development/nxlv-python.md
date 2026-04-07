# Evaluierung @nxlv/python

Das Paket [`@nxlv/python`](https://www.npmjs.com/package/@nxlv/python) erweitert das [Nx](https://nx.dev/) Build-System um Python-Unterstützung. ABrain verwendet jedoch keine Nx-Workspace-Struktur, sondern trennt Frontend und Backend konventionell.

Da weder das React-Frontend noch die Python-Services von Nx abhängig sind, würde die Einführung des Plugins keinen direkten Mehrwert bringen. Die bestehenden Skripte und die Poetry-Konfiguration decken das Build- und Dependency-Management bereits ab.

Eine Integration von @nxlv/python ist daher aktuell nicht vorgesehen.
