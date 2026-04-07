# Identity and Signatures

ABrain verwendet digitale Signaturen, um die Herkunft von Antworten
nachvollziehbar zu machen. Jeder Agent besitzt ein eigenes Ed25519-Schlüsselpaar
unter `keys/`. Beim Abschließen einer Aufgabe signiert der Agent die
zurückgegebenen Felder des `ModelContext`.

Der Dispatcher prüft die Signatur, sofern nicht über die
Umgebungsvariable `DISABLE_SIGNATURE_VALIDATION` deaktiviert.
Audit-Logs können optional eine Signatur enthalten, um Manipulationen
nachträglich aufzudecken.
