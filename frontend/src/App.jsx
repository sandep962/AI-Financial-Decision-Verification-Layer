import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [paymentId, setPaymentId] = useState("pay_TSsHeWcncbnKF5");
  const [record, setRecord] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function processPayment() {
    const id = paymentId.trim();

    if (!id) {
      setError("Enter a Razorpay Payment ID.");
      return;
    }

    setLoading(true);
    setError("");
    setRecord(null);

    try {
      const response = await fetch(
        `${API}/financial-events/from-razorpay/${encodeURIComponent(id)}/process`,
        {
          method: "POST",
        }
      );

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        throw new Error(
          data.error || "Unable to process payment."
        );
      }

      setRecord(data.record);
    } catch (err) {
      setError(err.message || "Backend connection failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <div className="eyebrow">
            RAZORPAY AI BUILDATHON
          </div>

          <h1>AI Financial Decision Layer</h1>

          <p>
            Context → Evidence → Decision → Policy → Verification
          </p>
        </div>

        <div className="live">
          <span className="dot"></span>
          BACKEND CONNECTED
        </div>
      </header>

      <main>
        <section className="processor">
          <div>
            <span className="label">
              PROCESS RAZORPAY PAYMENT
            </span>

            <h2>Run financial decision analysis</h2>

            <p>
              Enter a Razorpay Test Mode Payment ID.
            </p>
          </div>

          <div className="processor-form">
          <div className="demo-row">
          <button
            className="demo-button"
            onClick={async () => {
              setLoading(true);
              setError("");
              setRecord(null);

              try {
                const response = await fetch(
                  `${API}/financial-events/demo-failure/process`,
                  {
                    method: "POST",
                  }
                );

                const data = await response.json();

                if (!response.ok || data.status === "error") {
                  throw new Error(
                    data.error || "Demo processing failed."
                  );
                }

                setRecord(data.record);
              } catch (err) {
                setError(
                  err.message || "Unable to run demo."
                );
              } finally {
                setLoading(false);
              }
            }}
            disabled={loading}
          >
            RUN FAILED-PAYMENT DEMO
          </button>

          <span>
            Development simulation — no real payment action
          </span>
        </div>
            <input
              value={paymentId}
              onChange={(e) =>
                setPaymentId(e.target.value)
              }
              placeholder="pay_XXXXXXXXXXXX"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  processPayment();
                }
              }}
            />

            <button
              onClick={processPayment}
              disabled={loading}
            >
              {loading
                ? "PROCESSING..."
                : "PROCESS PAYMENT"}
            </button>
          </div>

          {error && (
            <div className="error-inline">
              {error}
            </div>
          )}
        </section>

        {!record && !loading && !error && (
          <section className="empty">
            <div className="empty-icon">→</div>
            <h2>Ready for a payment</h2>
            <p>
              Enter a Razorpay Payment ID above to start
              the complete decision pipeline.
            </p>
          </section>
        )}

        {loading && (
          <section className="empty">
            <div className="spinner"></div>
            <h2>Processing payment...</h2>
            <p>
              Fetching evidence and running the decision
              pipeline.
            </p>
          </section>
        )}

        {record && <DecisionDashboard record={record} />}
      </main>
    </div>
  );
}


function DecisionDashboard({ record }) {
  const payment = record.event;
  const evidence = record.evidence;
  const decision = record.decision;
  const policy = record.policy;
  const execution = record.execution;
  const verification = record.verification;

  return (
    <>
      <section className="payment-card">
        <div>
          <span className="label">PAYMENT</span>

          <h2>
            ₹
            {Number(payment.amount).toLocaleString(
              "en-IN"
            )}
          </h2>

          <p className="payment-id">
            {payment.payment_id}
          </p>
        </div>

        <div className="status-block">
          <span className="status success">
            {payment.status.toUpperCase()}
          </span>

          <span className="method">
            {payment.method}
          </span>
        </div>
      </section>

      <section className="pipeline">
        <Step
          number="01"
          title="Financial Event"
          status="COMPLETE"
          description={`Payment ${payment.payment_id} received from Razorpay.`}
        />

        <Step
          number="02"
          title="Evidence"
          status="COMPLETE"
          description={`Source: ${evidence.source}`}
        >
          <div className="details">
            <span>Amount</span>
            <strong>
              ₹
              {Number(
                evidence.payment.amount
              ).toLocaleString("en-IN")}
            </strong>

            <span>Order</span>
            <strong>
              {evidence.payment.order_id}
            </strong>

            <span>Captured</span>
            <strong>
              {String(
                evidence.payment.captured
              )}
            </strong>
          </div>
        </Step>

        <Step
          number="03"
          title="AI Decision"
          status="COMPLETE"
          description={decision.reason}
        >
          <div className="decision-box">
            <span>ROOT CAUSE</span>
            <strong>
              {decision.root_cause}
            </strong>

            <span>RECOMMENDED ACTION</span>
            <strong>
              {decision.recommended_action}
            </strong>
          </div>
        </Step>

        <Step
          number="04"
          title="Policy Check"
          status={policy.decision}
          description={policy.reasons.join(" • ")}
        >
          <div className="policy-row">
            <span>Execution permitted</span>

            <strong>
              {policy.execution_permitted
                ? "YES"
                : "NO"}
            </strong>
          </div>
        </Step>

        <Step
          number="05"
          title="Execution"
          status={
            execution.executed
              ? "EXECUTED"
              : "NOT REQUIRED"
          }
          description={execution.reason}
        />

        <Step
          number="06"
          title="Verification"
          status={
            verification.verified
              ? "VERIFIED"
              : "NOT VERIFIED"
          }
          description={
            verification.verified
              ? "Razorpay independently confirmed the final payment state."
              : "Final state could not be verified."
          }
        >
          <div className="verification">
            <div>
              <span>EXPECTED</span>
              <strong>
                {verification.expected}
              </strong>
            </div>

            <div>
              <span>ACTUAL</span>
              <strong>
                {verification.actual}
              </strong>
            </div>

            <div>
              <span>SOURCE</span>
              <strong>
                {verification.source}
              </strong>
            </div>
          </div>
        </Step>
      </section>

      <section className="audit">
        <div>
          <span className="label">
            AUDIT RECORD
          </span>

          <h2>Complete decision trail</h2>
        </div>

        <div className="audit-id">
          EVENT ID

          <strong>{record.event_id}</strong>
        </div>
      </section>
    </>
  );
}


function Step({
  number,
  title,
  status,
  description,
  children,
}) {
  const positive =
    status === "COMPLETE" ||
    status === "VERIFIED" ||
    status === "NO_ACTION";

  return (
    <article className="step">
      <div className="step-number">
        {number}
      </div>

      <div className="step-content">
        <div className="step-heading">
          <div>
            <h3>{title}</h3>
            <p>{description}</p>
          </div>

          <span
            className={`step-status ${
              positive ? "positive" : ""
            }`}
          >
            {status}
          </span>
        </div>

        {children}
      </div>
    </article>
  );
}


export default App;