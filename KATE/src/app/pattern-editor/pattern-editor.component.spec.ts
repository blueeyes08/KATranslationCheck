import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { PatternEditorComponent } from './pattern-editor.component';

describe('PatternEditorComponent', () => {
  let component: PatternEditorComponent;
  let fixture: ComponentFixture<PatternEditorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ PatternEditorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(PatternEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
