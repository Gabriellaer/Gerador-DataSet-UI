"""Executa tarefa em thread, redireciona print/warnings para o log."""

import contextlib
import io
import queue
import threading
import traceback
import warnings


def executar(root, progresso, log, tarefa, ao_terminar=None):
    q = queue.Queue()

    def worker():
        buf_out, buf_err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
                with warnings.catch_warnings(record=True) as ws:
                    warnings.simplefilter("always")
                    resultado = tarefa()
            q.put(("ok", resultado, buf_out.getvalue(), buf_err.getvalue(),
                   [f"{w.category.__name__}: {w.message}" for w in ws]))
        except Exception:
            q.put(("erro", None, buf_out.getvalue(), buf_err.getvalue(),
                   traceback.format_exc()))

    threading.Thread(target=worker, daemon=True).start()

    def poll():
        try:
            status, resultado, saida, erro_saida, extra = q.get_nowait()
        except queue.Empty:
            root.after(120, poll)
            return
        log.limpa()
        if saida:
            log.escreve(saida)
        if erro_saida:
            log.escreve(erro_saida, "erro")
        if status == "erro":
            log.escreve(extra + "\n", "erro")
        else:
            for w in extra:
                log.escreve(f"AVISO: {w}\n", "aviso")
        progresso.parar()
        if ao_terminar:
            ao_terminar(status, resultado)

    progresso.iniciar()
    root.after(120, poll)
