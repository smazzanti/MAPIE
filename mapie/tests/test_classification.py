from __future__ import annotations

from typing import Any, Optional, Tuple
from typing_extensions import TypedDict

import pytest
import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.datasets import make_classification
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.exceptions import NotFittedError
from sklearn.linear_model import LogisticRegression
from sklearn.utils.validation import check_is_fitted
from sklearn.dummy import DummyClassifier
from sklearn.naive_bayes import GaussianNB

from mapie.classification import MapieClassifier
from mapie.metrics import classification_coverage_score


METHODS = ["score", "cumulated_score"]

Params = TypedDict(
    "Params", {
        "method": str,
        "cv": Optional[str],
        "random_sets": Optional[bool],
        "random_state": Optional[int]
    }
)

STRATEGIES = {
    "score": Params(
        method="score",
        cv="prefit",
        random_sets=False,
        random_state=None
    ),
    "cumulated_score": Params(
        method="cumulated_score",
        cv="prefit",
        random_sets=True,
        random_state=42
    )
}

COVERAGES = {
    "score": 7/9,
    "cumulated_score": 7/9
}

y_toy_mapie = {
    "score": [
        [True, False, False],
        [True, False, False],
        [True, False, False],
        [True, True, False],
        [False, True, False],
        [False, True, True],
        [False, False, True],
        [False, False, True],
        [False, False, True]
    ],
    "cumulated_score": [
        [True, False, False],
        [True, False, False],
        [True, True, False],
        [True, True, False],
        [False, True, False],
        [False, True, False],
        [False, False, True],
        [False, False, True],
        [False, False, True]
    ]
}
X_toy = np.arange(9).reshape(-1, 1)
y_toy = np.array([0, 0, 1, 0, 1, 2, 1, 2, 2])

n_classes = 4
X, y = make_classification(
    n_samples=500,
    n_features=10,
    n_informative=3,
    n_classes=n_classes,
    random_state=1
)


class CumulatedscoreClassifier:

    def __init__(self) -> None:
        self.X_calib = np.array([0, 1, 2]).reshape(-1, 1)
        self.y_calib = np.array([0, 1, 2])
        self.y_calib_scores = np.array(
            [[0.64981605], [0.57042858], [0.97319939]]
        )
        self.X_test = np.array([3, 4, 5]).reshape(-1, 1)
        self.y_pred_sets = np.array(
            [[False, True, False], [False, False, True], [True, True, False]]
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> CumulatedscoreClassifier:
        self.fitted_ = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return np.array([1, 2, 1])

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if np.max(X) <= 2:
            return np.array(
                [[0.4, 0.5, 0.1], [0.2, 0.6, 0.2], [0.6, 0.3, 0.1]]
            )
        else:
            return np.array(
                [[0.2, 0.7, 0.1], [0.1, 0.2, 0.7], [0.3, 0.5, 0.2]]
            )


def test_default_parameters() -> None:
    """Test default values of input parameters."""
    mapie = MapieClassifier()
    assert mapie.estimator is None
    assert mapie.method == "score"
    assert mapie.cv == "prefit"
    assert mapie.random_sets is False
    assert mapie.verbose == 0
    assert mapie.random_state is None
    assert mapie.n_jobs is None


def test_none_estimator() -> None:
    """Test that None estimator defaults to LogisticRegression."""
    mapie = MapieClassifier(estimator=None)
    mapie.fit(X_toy, y_toy)
    assert isinstance(mapie.single_estimator_, LogisticRegression)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_valid_estimator(strategy: str) -> None:
    """Test that valid estimators are not corrupted, for all strategies."""
    clf = LogisticRegression().fit(X_toy, y_toy)
    mapie = MapieClassifier(
        estimator=clf,
        **STRATEGIES[strategy]
    )
    mapie.fit(X_toy, y_toy)
    assert isinstance(mapie.single_estimator_, LogisticRegression)


@pytest.mark.parametrize(
    "estimator", [LogisticRegression(), make_pipeline(LogisticRegression())]
)
def test_invalid_prefit_estimator(estimator: ClassifierMixin) -> None:
    """Test that non-fitted estimator with prefit cv raise errors."""
    mapie = MapieClassifier(estimator=estimator, cv="prefit")
    with pytest.raises(NotFittedError):
        mapie.fit(X_toy, y_toy)


@pytest.mark.parametrize(
    "estimator", [LogisticRegression(), make_pipeline(LogisticRegression())]
)
def test_valid_prefit_estimator(estimator: ClassifierMixin) -> None:
    """Test that fitted estimators with prefit cv raise no errors."""
    estimator.fit(X_toy, y_toy)
    mapie = MapieClassifier(estimator=estimator, cv="prefit")
    mapie.fit(X_toy, y_toy)
    check_is_fitted(mapie, mapie.fit_attributes)
    assert mapie.n_features_in_ == 1


@pytest.mark.parametrize(
    "method", [0.5, 1, "jackknife", "cv", ["base", "plus"]]
)
def test_invalid_method(method: str) -> None:
    """Test that invalid methods raise errors."""
    mapie = MapieClassifier(method=method)
    with pytest.raises(ValueError, match=r".*Invalid method.*"):
        mapie.fit(X_toy, y_toy)


@pytest.mark.parametrize("method", METHODS)
def test_valid_method(method: str) -> None:
    """Test that valid methods raise no errors."""
    mapie = MapieClassifier(method=method)
    mapie.fit(X_toy, y_toy)
    check_is_fitted(mapie, mapie.fit_attributes)

@pytest.mark.parametrize(
    "cv", [-3.14, 1.5, -2, 0, 1, "cv", DummyClassifier(), [1, 2]]
)
def test_invalid_cv(cv: Any) -> None:
    """Test that invalid cv raise errors."""
    mapie = MapieClassifier(cv=cv)
    with pytest.raises(ValueError, match=r".*Invalid cv argument.*"):
        mapie.fit(X_toy, y_toy)


@pytest.mark.parametrize("cv", [None, "prefit"])
def test_valid_cv(cv: Any) -> None:
    """Test that valid cv raise no errors."""
    model = LogisticRegression(multi_class="multinomial")
    model.fit(X_toy, y_toy)
    mapie = MapieClassifier(estimator=model, cv=cv)
    mapie.fit(X_toy, y_toy)


@pytest.mark.parametrize(
    "random_sets", [-3.14, 1.5, -2, 0, 1, "cv", DummyClassifier(), [1, 2]]
)
def test_invalid_random_sets(random_sets: Any) -> None:
    """Test that invalid random_sets raise errors."""
    mapie = MapieClassifier(random_sets=random_sets)
    with pytest.raises(ValueError, match=r".*Invalid random_sets argument.*"):
        mapie.fit(X_toy, y_toy)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
@pytest.mark.parametrize("dataset", [(X, y), (X_toy, y_toy)])
@pytest.mark.parametrize("alpha", [0.2, [0.2, 0.3], (0.2, 0.3)])
def test_predict_output_shape(
    strategy: str, alpha: Any, dataset: Tuple[np.ndarray, np.ndarray]
) -> None:
    """Test predict output shape."""
    mapie = MapieClassifier(**STRATEGIES[strategy])
    X, y = dataset
    mapie.fit(X, y)
    y_pred, y_ps = mapie.predict(X, alpha=alpha)
    n_alpha = len(alpha) if hasattr(alpha, "__len__") else 1
    assert y_pred.shape == (X.shape[0],)
    assert y_ps.shape == (X.shape[0], len(np.unique(y)), n_alpha)


def test_none_alpha_results() -> None:
    """
    Test that alpha set to None in MapieClassifier gives same predictions
    as base Classifier.
    """
    estimator = LogisticRegression()
    estimator.fit(X, y)
    y_pred_est = estimator.predict(X)
    mapie = MapieClassifier(estimator=estimator, cv="prefit")
    mapie.fit(X, y)
    y_pred_mapie = mapie.predict(X)
    np.testing.assert_allclose(y_pred_est, y_pred_mapie)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_results_for_same_alpha(strategy: str) -> None:
    """
    Test that predictions and intervals
    are similar with two equal values of alpha.
    """
    mapie = MapieClassifier(**STRATEGIES[strategy])
    mapie.fit(X, y)
    _, y_ps = mapie.predict(X, alpha=[0.1, 0.1])
    np.testing.assert_allclose(y_ps[:, 0, 0], y_ps[:, 0, 1])
    np.testing.assert_allclose(y_ps[:, 1, 0], y_ps[:, 1, 1])


@pytest.mark.parametrize("strategy", [*STRATEGIES])
@pytest.mark.parametrize(
    "alpha", [np.array([0.05, 0.1]), [0.05, 0.1], (0.05, 0.1)]
)
def test_results_for_alpha_as_float_and_arraylike(
    strategy: str,
    alpha: Any
) -> None:
    """Test that output values do not depend on type of alpha."""
    mapie = MapieClassifier(**STRATEGIES[strategy])
    mapie.fit(X, y)
    y_pred_float1, y_ps_float1 = mapie.predict(X, alpha=alpha[0])
    y_pred_float2, y_ps_float2 = mapie.predict(X, alpha=alpha[1])
    y_pred_array, y_ps_array = mapie.predict(X, alpha=alpha)
    np.testing.assert_allclose(y_pred_float1, y_pred_array)
    np.testing.assert_allclose(y_pred_float2, y_pred_array)
    np.testing.assert_allclose(y_ps_float1[:, :, 0], y_ps_array[:, :, 0])
    np.testing.assert_allclose(y_ps_float2[:, :, 0], y_ps_array[:, :, 1])


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_results_single_and_multi_jobs(strategy: str) -> None:
    """
    Test that MapieRegressor gives equal predictions
    regardless of number of parallel jobs.
    """
    mapie_single = MapieClassifier(n_jobs=1, **STRATEGIES[strategy])
    mapie_multi = MapieClassifier(n_jobs=-1, **STRATEGIES[strategy])
    mapie_single.fit(X_toy, y_toy)
    mapie_multi.fit(X_toy, y_toy)
    y_pred_single, y_ps_single = mapie_single.predict(X_toy, alpha=0.2)
    y_pred_multi, y_ps_multi = mapie_multi.predict(X_toy, alpha=0.2)
    np.testing.assert_allclose(y_pred_single, y_pred_multi)
    np.testing.assert_allclose(y_ps_single, y_ps_multi)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_results_with_constant_sample_weights(strategy: str) -> None:
    """
    Test predictions when sample weights are None
    or constant with different values.
    """
    n_samples = len(X_toy)
    mapie0 = MapieClassifier(**STRATEGIES[strategy])
    mapie1 = MapieClassifier(**STRATEGIES[strategy])
    mapie2 = MapieClassifier(**STRATEGIES[strategy])
    mapie0.fit(X_toy, y_toy, sample_weight=None)
    mapie1.fit(X_toy, y_toy, sample_weight=np.ones(shape=n_samples))
    mapie2.fit(X_toy, y_toy, sample_weight=np.ones(shape=n_samples)*5)
    y_pred0, y_ps0 = mapie0.predict(X_toy, alpha=0.2)
    y_pred1, y_ps1 = mapie1.predict(X_toy, alpha=0.2)
    y_pred2, y_ps2 = mapie2.predict(X_toy, alpha=0.2)
    np.testing.assert_allclose(y_pred0, y_pred1)
    np.testing.assert_allclose(y_pred0, y_pred2)
    np.testing.assert_allclose(y_ps0, y_ps1)
    np.testing.assert_allclose(y_ps0, y_ps2)


@pytest.mark.parametrize(
    "alpha",
    [
        [0.2, 0.8],
        (0.2, 0.8),
        np.array([0.2, 0.8]),
        None
    ]
)
def test_valid_prediction(alpha: Any) -> None:
    """Test fit and predict. """
    model = LogisticRegression(multi_class="multinomial")
    model.fit(X_toy, y_toy)
    mapie = MapieClassifier(estimator=model, cv="prefit")
    mapie.fit(X_toy, y_toy)
    mapie.predict(X_toy, alpha=alpha)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_toy_dataset_predictions(strategy: str) -> None:
    """Test prediction sets estimated by MapieClassifier on a toy dataset"""
    clf = GaussianNB().fit(X_toy, y_toy)
    mapie = MapieClassifier(estimator=clf, **STRATEGIES[strategy])
    mapie.fit(X_toy, y_toy)
    _, y_ps = mapie.predict(X_toy, alpha=0.2)
    np.testing.assert_allclose(
        classification_coverage_score(y_toy, y_ps[:, :, 0]),
        COVERAGES[strategy]
    )
    np.testing.assert_allclose(y_ps[:, :, 0], y_toy_mapie[strategy])


def test_cumulated_scores() -> None:
    """Test cumulated score method on a tiny dataset."""
    alpha = [0.65]
    quantile = [0.57042858]
    # fit
    cumclf = CumulatedscoreClassifier()
    cumclf.fit(cumclf.X_calib, cumclf.y_calib)
    mapie = MapieClassifier(
        cumclf, method="cumulated_score", cv="prefit", random_state=42
    )
    mapie.fit(cumclf.X_calib, cumclf.y_calib)
    np.testing.assert_allclose(mapie.scores_, cumclf.y_calib_scores)
    # predict
    y_pred, y_ps = mapie.predict(cumclf.X_test, alpha=alpha)
    np.testing.assert_allclose(mapie.quantiles_, quantile)
    np.testing.assert_allclose(y_ps[:, :, 0], cumclf.y_pred_sets)