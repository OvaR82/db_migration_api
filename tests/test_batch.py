def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_batch_departments_insert_and_duplicate(client):
    items = [{"id": 1, "name": "Sales"}, {"id": 2, "name": "Legal"}]
    r = client.post("/departments/batch", json=items)
    assert r.status_code == 200
    assert r.json() == {"inserted": 2}

    r = client.post("/departments/batch", json=[{"id": 1, "name": "Otro"}])
    assert r.status_code == 409
    assert "Insert failed" not in r.text  # no se filtran errores crudos de la BD


def test_batch_size_limits(client):
    assert client.post("/jobs/batch", json=[]).status_code == 422
    too_many = [{"id": i, "title": f"Job {i}"} for i in range(1, 1002)]
    assert client.post("/jobs/batch", json=too_many).status_code == 422


def test_batch_employees_requires_existing_fk(client):
    client.post("/departments/batch", json=[{"id": 1, "name": "Sales"}])
    client.post("/jobs/batch", json=[{"id": 1, "title": "Rep"}])
    ok = {"id": 1, "name": "Ana", "department_id": 1, "job_id": 1, "hire_date": "2021-03-01"}
    assert client.post("/employees/batch", json=[ok]).status_code == 200

    bad = {**ok, "id": 2, "department_id": 99}
    assert client.post("/employees/batch", json=[bad]).status_code == 409


def test_batch_is_all_or_nothing(client):
    items = [{"id": 1, "name": "A"}, {"id": 1, "name": "B"}]
    assert client.post("/departments/batch", json=items).status_code == 409
    assert client.post("/departments/batch", json=[{"id": 1, "name": "A"}]).status_code == 200
