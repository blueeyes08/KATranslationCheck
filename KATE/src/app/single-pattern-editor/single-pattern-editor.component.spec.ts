import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SinglePatternEditorComponent } from './single-pattern-editor.component';

describe('SinglePatternEditorComponent', () => {
  let component: SinglePatternEditorComponent;
  let fixture: ComponentFixture<SinglePatternEditorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ SinglePatternEditorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(SinglePatternEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
